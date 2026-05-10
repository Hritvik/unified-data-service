"""HierarchicalUnifiedService — tree-aware orchestration over composed UnifiedDataService instances.

The hierarchical layer does not subclass UnifiedDataService. It composes one
service per node kind (looked up by kind name) and exposes tree-aware
operations that delegate to the per-level services for actual reads/writes.

Atomicity: cascade is best-effort with logged failures (config-repo grade).
For replica-set environments, optional Mongo session plumbing can be added
later without changing this surface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from common_utils.cache import ICacheRepository
from common_utils.logger import get_logger

from ..interfaces import (
    DataSourceQuery,
    HierarchyConfig,
    NodeConfig,
    ReferenceConfig,
)
from ..service import UnifiedDataService

logger = get_logger(__name__)


class TreeNode(BaseModel):
    """A single node in a get_with_descendants result.

    `entity` is the entity dict (model_dump) at this node.
    `children` maps child kind -> list of TreeNodes for that kind.
    `references` maps reference name -> resolved entity dicts.
    """

    kind: str
    entity: Dict[str, Any]
    children: Dict[str, List["TreeNode"]] = {}
    references: Dict[str, List[Dict[str, Any]]] = {}


TreeNode.model_rebuild()


class CascadeResult(BaseModel):
    """Outcome of a cascade delete."""

    deleted: Dict[str, int] = {}
    failed: Dict[str, List[Any]] = {}

    @property
    def total_deleted(self) -> int:
        return sum(self.deleted.values())

    @property
    def has_failures(self) -> bool:
        return any(self.failed.values())


class _NodeRuntime:
    """Internal: a node config bundled with its resolved service and parent/child pointers."""

    def __init__(self, config: NodeConfig, service: UnifiedDataService) -> None:
        self.config = config
        self.service = service
        self.parent: Optional[_NodeRuntime] = None
        self.children: List[_NodeRuntime] = []

    @property
    def kind(self) -> str:
        return self.config.kind

    @property
    def parent_field(self) -> Optional[str]:
        return self.config.parent_field

    @property
    def pk_field(self) -> str:
        return self.config.pk_field


class HierarchicalUnifiedService:
    """Orchestrates a tree of composed UnifiedDataService instances.

    Construct via HierarchicalServiceFactory.create_hierarchy; this constructor
    accepts an already-resolved {kind: UnifiedDataService} mapping for tests
    and direct wiring.
    """

    def __init__(
        self,
        config: HierarchyConfig,
        services: Dict[str, UnifiedDataService],
        subtree_cache: Optional[ICacheRepository] = None,
    ) -> None:
        self._config = config
        self._services = services
        self._subtree_cache = subtree_cache
        self._nodes: Dict[str, _NodeRuntime] = {}
        self._root: _NodeRuntime = self._build_tree(config.root, parent=None)
        self.logger = logger

    def _build_tree(
        self, node_config: NodeConfig, parent: Optional[_NodeRuntime]
    ) -> _NodeRuntime:
        if node_config.kind in self._nodes:
            raise ValueError(
                f"Duplicate node kind '{node_config.kind}' in hierarchy '{self._config.name}'"
            )
        if node_config.service_ref not in self._services:
            raise ValueError(
                f"No service registered for ref '{node_config.service_ref}' "
                f"(node kind '{node_config.kind}')"
            )
        if parent is None and node_config.parent_field is not None:
            raise ValueError(
                f"Root node '{node_config.kind}' must not declare a parent_field"
            )
        if parent is not None and node_config.parent_field is None:
            raise ValueError(
                f"Non-root node '{node_config.kind}' must declare parent_field"
            )
        if parent is not None and node_config.parent_kind != parent.kind:
            raise ValueError(
                f"Node '{node_config.kind}' declares parent_kind="
                f"'{node_config.parent_kind}' but tree parent is '{parent.kind}'"
            )

        runtime = _NodeRuntime(node_config, self._services[node_config.service_ref])
        runtime.parent = parent
        self._nodes[node_config.kind] = runtime
        for child_cfg in node_config.children:
            runtime.children.append(self._build_tree(child_cfg, parent=runtime))
        return runtime

    def _node(self, kind: str) -> _NodeRuntime:
        if kind not in self._nodes:
            raise KeyError(
                f"Unknown node kind '{kind}' in hierarchy '{self._config.name}'"
            )
        return self._nodes[kind]

    # ------------------------------------------------------------------
    # Read paths
    # ------------------------------------------------------------------
    async def get_with_descendants(
        self, kind: str, id: Any, depth: int = -1
    ) -> Optional[TreeNode]:
        """Fetch an entity and its descendants up to `depth`.

        depth=-1 means full tree. depth=0 returns just the entity, no children.
        References on the entity are resolved at read time.

        Returns None if the root entity is not found.
        """
        node = self._node(kind)
        cache_key = self._subtree_key(kind, id, depth)
        if self._subtree_cache is not None:
            cached = await self._subtree_cache.get_by_key(cache_key)
            if cached is not None:
                return cached if isinstance(cached, TreeNode) else TreeNode(**cached)

        entity = await node.service.get_by_id(id)
        if entity is None:
            return None

        tree = await self._build_subtree(node, entity, depth)

        if self._subtree_cache is not None:
            await self._subtree_cache.set_by_key(
                cache_key,
                tree,
                self._config.subtree_cache_ttl_seconds,
            )
            await self._register_reverse_pointers(tree, cache_key)

        return tree

    async def _build_subtree(
        self, node: _NodeRuntime, entity: Any, depth: int
    ) -> TreeNode:
        entity_dict = self._entity_to_dict(entity)
        tree = TreeNode(kind=node.kind, entity=entity_dict)

        # Resolve M:N references on this entity
        ref_configs = self._service_references(node.service)
        for ref in ref_configs:
            tree.references[ref.name] = await self._resolve_reference(entity, ref)

        # Recurse into children
        if depth != 0:
            parent_pk_value = self._pk_value(node, entity)
            child_depth = -1 if depth < 0 else depth - 1
            for child_node in node.children:
                children_entities = await child_node.service.get_entities_by_field_value(
                    child_node.parent_field, parent_pk_value
                )
                tree.children[child_node.kind] = [
                    await self._build_subtree(child_node, child, child_depth)
                    for child in children_entities
                ]

        return tree

    async def _resolve_reference(
        self, entity: Any, ref: ReferenceConfig
    ) -> List[Dict[str, Any]]:
        target_service = self._services.get(ref.target_service)
        if target_service is None:
            self.logger.warning(
                f"Reference '{ref.name}' targets unknown service '{ref.target_service}'"
            )
            return []
        raw = self._get_attr(entity, ref.field)
        if raw is None:
            return []
        if not isinstance(raw, list):
            raw = [raw]

        scope_filter: Dict[str, Any] = {}
        if ref.scope_field is not None:
            scope_value = self._get_attr(entity, ref.scope_field)
            if scope_value is None:
                # scope_field is configured but the referrer has no value
                # for it — refuse to resolve. Without this, the lookup
                # would fall through to an unscoped search and could
                # silently match targets from other scopes.
                self.logger.warning(
                    f"Reference '{ref.name}' has scope_field "
                    f"'{ref.scope_field}' configured but referrer has no "
                    f"value for it; returning empty"
                )
                return []
            scope_filter[ref.scope_field] = scope_value

        resolved: List[Dict[str, Any]] = []
        for item in raw:
            target_entity = await self._resolve_one_reference(
                target_service, item, ref.resolver, scope_filter
            )
            if target_entity is not None:
                resolved.append(self._entity_to_dict(target_entity))
        return resolved

    async def _resolve_one_reference(
        self,
        target_service: UnifiedDataService,
        ref_value: Any,
        resolver: str,
        scope_filter: Dict[str, Any],
    ) -> Optional[Any]:
        if resolver == "id":
            target_entity = await target_service.get_by_id(ref_value)
            if target_entity is None:
                return None
            for k, v in scope_filter.items():
                if self._get_attr(target_entity, k) != v:
                    return None
            return target_entity
        if resolver == "type.name":
            if not isinstance(ref_value, str) or "." not in ref_value:
                return None
            ctype, cname = ref_value.split(".", 1)
            filters = {
                "component_type": ctype,
                "component_name": cname,
                **scope_filter,
            }
            results = await target_service.search(
                DataSourceQuery(filters=filters, limit=1)
            )
            return results[0] if results else None
        # dotted-path / custom resolvers: treat as a filter dict {field: value}
        filters = {resolver: ref_value, **scope_filter}
        results = await target_service.search(
            DataSourceQuery(filters=filters, limit=1)
        )
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Cascade delete
    # ------------------------------------------------------------------
    async def delete_cascade(
        self,
        kind: str,
        id: Any,
        force_orphan_cleanup: bool = False,
        children_only: bool = False,
    ) -> CascadeResult:
        """Depth-first cascade delete.

        `id` is the value of the node's `pk_field` (a stable natural-key
        field — never a Mongo ObjectId or other ephemeral handle). Children
        at every level are deleted first, then the parent (unless
        children_only=True). force_orphan_cleanup=True allows cleanup when
        the root entity is missing but descendants still exist. Per-edge
        cascade policy:
          "delete":   children are deleted recursively
          "restrict": raises ValueError if children exist
          "detach":   children are left in place
        """
        node = self._node(kind)
        result = CascadeResult()

        root_entity = await node.service.get_by_id(id)
        if root_entity is None and not force_orphan_cleanup:
            return result

        await self._cascade_descendants(node, id, result)

        if not children_only and root_entity is not None:
            ok = await self._safe_delete(node, id, result)
            if ok:
                await self._invalidate_subtrees_for(node, id)

        return result

    async def _cascade_descendants(
        self, node: _NodeRuntime, parent_pk_value: Any, result: CascadeResult
    ) -> None:
        # Two passes: read everything first so a `restrict` violation in any
        # child kind aborts before we've deleted entities under a sibling
        # `delete`-policy edge. Without this, iteration order would matter.
        deletable: List[tuple] = []
        for child_node in node.children:
            policy = child_node.config.cascade
            try:
                children = await child_node.service.get_entities_by_field_value(
                    child_node.parent_field, parent_pk_value
                )
            except Exception as e:
                # Read failure for one child kind shouldn't abort the whole
                # cascade — record and move on (best-effort contract).
                self.logger.error(
                    f"Cascade read failed on {child_node.kind} "
                    f"(parent={node.kind}, parent_pk={parent_pk_value}): {e}",
                    exc_info=True,
                )
                result.failed.setdefault(
                    f"read_failures:{child_node.kind}", []
                ).append(parent_pk_value)
                continue
            if not children:
                continue
            if policy == "restrict":
                raise ValueError(
                    f"Cannot cascade-delete '{node.kind}' (id={parent_pk_value}): "
                    f"{len(children)} child '{child_node.kind}' entities exist "
                    f"and cascade=restrict"
                )
            if policy == "detach":
                continue
            deletable.append((child_node, children))

        for child_node, children in deletable:
            for child in children:
                child_pk = self._pk_value(child_node, child)
                # Recurse first so we delete grandchildren before child.
                await self._cascade_descendants(child_node, child_pk, result)
                await self._safe_delete(child_node, child_pk, result)
                await self._invalidate_subtrees_for(child_node, child_pk)

    async def _safe_delete(
        self, node: _NodeRuntime, pk_value: Any, result: CascadeResult
    ) -> bool:
        try:
            ok = await node.service.delete(pk_value)
            if ok:
                result.deleted[node.kind] = result.deleted.get(node.kind, 0) + 1
            else:
                result.failed.setdefault(node.kind, []).append(pk_value)
            return ok
        except Exception as e:
            self.logger.error(
                f"Cascade delete failed on {node.kind} pk={pk_value}: {e}",
                exc_info=True,
            )
            result.failed.setdefault(node.kind, []).append(pk_value)
            return False

    # ------------------------------------------------------------------
    # Tree mutations
    # ------------------------------------------------------------------
    async def create_with_children(
        self,
        kind: str,
        data: Dict[str, Any],
        children: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> TreeNode:
        """Create a parent entity and recursively create its children.

        children is {child_kind: [child_data, ...]}. Each child_data may itself
        contain a nested `children` key (recursive).

        Best-effort: failures during child creation are logged; the parent
        is still returned. Use force_orphan_cleanup on a subsequent
        delete_cascade to clean up partials.
        """
        node = self._node(kind)
        if children is not None:
            self._validate_children_payload(node, children)
        entity = await node.service.create(data)
        parent_pk_value = self._pk_value(node, entity)
        tree = TreeNode(kind=node.kind, entity=self._entity_to_dict(entity))

        if children:
            for child_kind, child_data_list in children.items():
                child_node = self._child_node_or_raise(node, child_kind)
                tree.children[child_kind] = []
                for child_data in child_data_list:
                    nested_children = child_data.get("children")
                    payload = {
                        k: v for k, v in child_data.items() if k != "children"
                    }
                    payload[child_node.parent_field] = parent_pk_value
                    try:
                        child_tree = await self.create_with_children(
                            child_kind, payload, nested_children
                        )
                        tree.children[child_kind].append(child_tree)
                    except Exception as e:
                        self.logger.error(
                            f"create_with_children child create failed on "
                            f"{child_kind} (parent={node.kind}, "
                            f"parent_pk={parent_pk_value}): {e}",
                            exc_info=True,
                        )

        await self._invalidate_subtrees_for(node, parent_pk_value)
        # Non-root creates also dirty the parent's subtree cache: any cached
        # tree of the parent now misses this newly created child.
        if node.parent is not None:
            parent_field_value = self._get_attr(entity, node.parent_field)
            if parent_field_value is not None:
                await self._invalidate_subtrees_for(node.parent, parent_field_value)
        return tree

    # ------------------------------------------------------------------
    # Subtree cache helpers
    # ------------------------------------------------------------------
    def _subtree_key(self, kind: str, id: Any, depth: int) -> str:
        return f"{self._config.subtree_cache_key_prefix}:{kind}:{id}:{depth}"

    def _reverse_pointer_key(self, kind: str, id: Any) -> str:
        return f"{self._config.subtree_cache_key_prefix}_index:{kind}:{id}"

    async def _register_reverse_pointers(
        self, tree: TreeNode, subtree_key: str
    ) -> None:
        if self._subtree_cache is None:
            return
        # Walk the tree and append subtree_key to each entity's reverse pointer.
        # Implementation is best-effort and idempotent: cache is a single value
        # per pointer; if the cache backend doesn't support sets, we store a
        # list-typed value.
        for kind, eid in self._iter_tree_entities(tree):
            ptr_key = self._reverse_pointer_key(kind, eid)
            existing = await self._subtree_cache.get_by_key(ptr_key)
            keys: List[str] = list(existing) if isinstance(existing, list) else []
            if subtree_key not in keys:
                keys.append(subtree_key)
                await self._subtree_cache.set_by_key(
                    ptr_key, keys, self._config.subtree_cache_ttl_seconds
                )

    async def _invalidate_subtrees_for(
        self, node: _NodeRuntime, id: Any
    ) -> None:
        if self._subtree_cache is None:
            return
        ptr_key = self._reverse_pointer_key(node.kind, id)
        existing = await self._subtree_cache.get_by_key(ptr_key)
        if isinstance(existing, list):
            for subtree_key in existing:
                await self._subtree_cache.delete_by_key(subtree_key)
            await self._subtree_cache.delete_by_key(ptr_key)

    def _iter_tree_entities(self, tree: TreeNode):
        node = self._nodes.get(tree.kind)
        pk_field = node.pk_field if node is not None else "id"
        pk_value = tree.entity.get(pk_field)
        if pk_value is not None:
            yield tree.kind, pk_value
        for child_list in tree.children.values():
            for child_tree in child_list:
                yield from self._iter_tree_entities(child_tree)

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def _service_references(
        self, service: UnifiedDataService
    ) -> List[ReferenceConfig]:
        cfg = getattr(service, "_config", None)
        if cfg is None:
            return []
        return list(getattr(cfg, "references", []))

    def _validate_children_payload(
        self, parent: _NodeRuntime, children: Any
    ) -> None:
        """Pre-flight check on the create_with_children children dict.

        Walks the full nested structure so a malformed payload aborts
        before any parent is written, preventing partial trees.
        """
        if not isinstance(children, dict):
            raise ValueError(
                f"children must be a dict mapping child_kind -> list[dict], "
                f"got {type(children).__name__}"
            )
        for child_kind, child_data_list in children.items():
            child_node = self._child_node_or_raise(parent, child_kind)
            if not isinstance(child_data_list, list):
                raise ValueError(
                    f"children['{child_kind}'] must be a list, "
                    f"got {type(child_data_list).__name__}"
                )
            for i, child_data in enumerate(child_data_list):
                if not isinstance(child_data, dict):
                    raise ValueError(
                        f"children['{child_kind}'][{i}] must be a dict, "
                        f"got {type(child_data).__name__}"
                    )
                nested = child_data.get("children")
                if nested is None:
                    continue
                if not isinstance(nested, dict):
                    raise ValueError(
                        f"children['{child_kind}'][{i}]['children'] must be "
                        f"a dict or None, got {type(nested).__name__}"
                    )
                self._validate_children_payload(child_node, nested)

    def _child_node_or_raise(
        self, parent: _NodeRuntime, child_kind: str
    ) -> _NodeRuntime:
        for child in parent.children:
            if child.kind == child_kind:
                return child
        raise KeyError(
            f"'{child_kind}' is not a direct child of '{parent.kind}' "
            f"in hierarchy '{self._config.name}'"
        )

    @staticmethod
    def _pk_value(node: _NodeRuntime, entity: Any) -> Any:
        """Extract the natural-key (pk_field) value from an entity."""
        if isinstance(entity, dict):
            return entity.get(node.pk_field)
        return getattr(entity, node.pk_field, None)

    # Fields stripped from every exported entity before re-import. These
    # are storage-layer internals (Beanie ObjectId / Mongo _id / Beanie
    # state revision) that would collide with the original on a clone
    # import — fresh values are generated server-side instead.
    _EXPORT_DROP_FIELDS = ("id", "_id", "revision_id")

    @classmethod
    def flatten_for_import(cls, tree: "TreeNode") -> Dict[str, Any]:
        """Convert a TreeNode subtree into the flat ``{...entity_fields,
        children: {kind: [...]}}`` shape that ``create_with_children``
        consumes — so an export round-trips into an import.

        References (the M:N read-time projections) are deliberately
        dropped: they are read-only views, and the M:N targets re-resolve
        naturally on import (the resolver scopes by parent_id). Storage
        internals (id/_id/revision_id) are also dropped so cloned imports
        get fresh values.
        """
        out: Dict[str, Any] = {
            k: v for k, v in tree.entity.items() if k not in cls._EXPORT_DROP_FIELDS
        }
        if tree.children:
            out["children"] = {
                child_kind: [cls.flatten_for_import(child) for child in child_list]
                for child_kind, child_list in tree.children.items()
            }
        return out

    @staticmethod
    def _entity_to_dict(entity: Any) -> Dict[str, Any]:
        """Serialize an entity to a JSON-friendly dict.

        For Beanie/pydantic documents we use ``mode="json"`` so non-JSON
        types (PydanticObjectId, datetime, Enum, etc.) get coerced to
        their JSON representations up front — without that, downstream
        FastAPI/pydantic_core serialization fails on PydanticObjectId
        when the dict is later returned through an HTTP response.
        """
        if isinstance(entity, dict):
            return entity
        if hasattr(entity, "model_dump"):
            try:
                return entity.model_dump(mode="json")
            except TypeError:
                return entity.model_dump()
        if hasattr(entity, "dict"):
            return entity.dict()
        return {k: v for k, v in vars(entity).items() if not k.startswith("_")}

    @staticmethod
    def _get_attr(entity: Any, name: str) -> Any:
        if isinstance(entity, dict):
            return entity.get(name)
        return getattr(entity, name, None)
