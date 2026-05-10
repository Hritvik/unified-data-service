"""Contract tests for HierarchicalUnifiedService.

Uses an in-memory fake of UnifiedDataService that implements only the
methods the hierarchical layer relies on. This deliberately avoids
spinning up MongoDB or Redis so tests run in-process.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import pytest

from common_utils.unified_data.hierarchical import (
    CascadeResult,
    HierarchicalUnifiedService,
)
from common_utils.unified_data.interfaces import (
    DataSourceQuery,
    HierarchyConfig,
    NodeConfig,
    ReferenceConfig,
    ServiceConfig,
)


class FakeService:
    """Minimal stand-in for UnifiedDataService — supports the methods the
    hierarchical layer calls, plus a fault injector for cascade-failure tests.

    `key_field` matches the V2 design: services with a natural-key (e.g.
    `name`) set key_field="name" so lookups go through that field. The
    in-memory store is still indexed on the natural key for simplicity.
    """

    def __init__(
        self,
        references: Optional[List[ReferenceConfig]] = None,
        key_field: str = "id",
    ) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._fail_on_delete_id: Optional[str] = None
        self._key_field = key_field
        self._config = ServiceConfig(
            name=f"fake_{uuid.uuid4().hex[:6]}",
            entity_type="Dict",
            data_source={"type": "mongodb", "key_field": key_field},
            references=references or [],
        )

    async def get_by_id(self, id: Any) -> Optional[Dict[str, Any]]:
        return self._store.get(id)

    async def get_entities_by_field_value(
        self, field_name: str, field_value: Any
    ) -> List[Dict[str, Any]]:
        return [e for e in self._store.values() if e.get(field_name) == field_value]

    async def search(self, query: DataSourceQuery) -> List[Dict[str, Any]]:
        items = list(self._store.values())
        if query.filters:
            items = [
                e for e in items
                if all(e.get(k) == v for k, v in query.filters.items())
            ]
        if query.limit is not None:
            items = items[: query.limit]
        return items

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        entity = dict(data)
        if self._key_field not in entity:
            entity[self._key_field] = uuid.uuid4().hex
        self._store[entity[self._key_field]] = entity
        return entity

    async def update(
        self, id: Any, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if id not in self._store:
            return None
        self._store[id].update(data)
        return self._store[id]

    async def delete(self, id: Any) -> bool:
        if self._fail_on_delete_id == id:
            raise RuntimeError(f"injected delete failure for {id}")
        return self._store.pop(id, None) is not None

    # Test-helpers
    def fail_next_delete(self, id: str) -> None:
        self._fail_on_delete_id = id

    def all_ids(self) -> List[str]:
        return list(self._store.keys())


class FakeCache:
    """Tiny in-memory cache that mimics ICacheRepository's set/get/delete."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    async def get_by_key(self, key: str) -> Any:
        return self._store.get(key)

    async def set_by_key(self, key: str, value: Any, ttl: Optional[int] = None) -> Any:
        self._store[key] = value
        return value

    async def delete_by_key(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def keys(self) -> List[str]:
        return list(self._store.keys())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _three_level_config() -> HierarchyConfig:
    """namespace -> [template, component]; template references components M:N."""
    return HierarchyConfig(
        name="prompt_tree",
        root=NodeConfig(
            kind="namespace",
            service_ref="namespace_svc",
            children=[
                NodeConfig(
                    kind="template",
                    service_ref="template_svc",
                    parent_field="namespace_id",
                    parent_kind="namespace",
                    cascade="delete",
                ),
                NodeConfig(
                    kind="component",
                    service_ref="component_svc",
                    parent_field="namespace_id",
                    parent_kind="namespace",
                    cascade="delete",
                ),
            ],
        ),
    )


def _make_services() -> Dict[str, FakeService]:
    template_refs = [
        ReferenceConfig(
            name="components",
            field="components",
            target_service="component_svc",
            resolver="type.name",
        )
    ]
    return {
        "namespace_svc": FakeService(),
        "template_svc": FakeService(references=template_refs),
        "component_svc": FakeService(),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tree_construction_validates_shape():
    services = _make_services()
    bad_root = HierarchyConfig(
        name="bad",
        root=NodeConfig(
            kind="namespace",
            service_ref="namespace_svc",
            parent_field="x",  # root must not declare parent_field
        ),
    )
    with pytest.raises(ValueError, match="must not declare a parent_field"):
        HierarchicalUnifiedService(bad_root, services)


@pytest.mark.asyncio
async def test_create_with_children_three_levels_and_get_with_descendants():
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    tree = await h.create_with_children(
        "namespace",
        {"id": "ns1", "description": "checkout"},
        {
            "template": [{"id": "t1", "name": "greet", "components": []}],
            "component": [
                {
                    "id": "c1",
                    "component_type": "header",
                    "component_name": "hi",
                    "content": "hello",
                }
            ],
        },
    )
    assert tree.kind == "namespace"
    assert tree.entity["id"] == "ns1"
    assert {c.entity["id"] for c in tree.children["template"]} == {"t1"}
    assert {c.entity["id"] for c in tree.children["component"]} == {"c1"}

    # Now read it back
    fetched = await h.get_with_descendants("namespace", "ns1", depth=-1)
    assert fetched is not None
    assert fetched.entity["id"] == "ns1"
    assert {c.entity["id"] for c in fetched.children["template"]} == {"t1"}
    assert {c.entity["id"] for c in fetched.children["component"]} == {"c1"}

    # depth=0 returns no children
    shallow = await h.get_with_descendants("namespace", "ns1", depth=0)
    assert shallow is not None
    assert shallow.children == {}


@pytest.mark.asyncio
async def test_get_with_descendants_resolves_mn_references():
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    await services["namespace_svc"].create({"id": "ns1", "description": "ns"})
    await services["component_svc"].create(
        {
            "id": "c1",
            "namespace_id": "ns1",
            "component_type": "header",
            "component_name": "hi",
            "content": "hello",
        }
    )
    await services["template_svc"].create(
        {
            "id": "t1",
            "namespace_id": "ns1",
            "name": "greet",
            "components": ["header.hi"],
        }
    )

    tree = await h.get_with_descendants("namespace", "ns1")
    assert tree is not None
    [template_tree] = tree.children["template"]
    resolved = template_tree.references["components"]
    assert len(resolved) == 1
    assert resolved[0]["component_type"] == "header"
    assert resolved[0]["component_name"] == "hi"


@pytest.mark.asyncio
async def test_delete_cascade_removes_full_subtree():
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    await h.create_with_children(
        "namespace",
        {"id": "ns1", "description": "x"},
        {
            "template": [{"id": "t1", "name": "x"}, {"id": "t2", "name": "y"}],
            "component": [
                {
                    "id": "c1",
                    "component_type": "h",
                    "component_name": "n",
                    "content": "v",
                }
            ],
        },
    )
    result = await h.delete_cascade("namespace", "ns1")
    assert isinstance(result, CascadeResult)
    assert result.deleted == {"template": 2, "component": 1, "namespace": 1}
    assert not result.has_failures
    assert services["namespace_svc"].all_ids() == []
    assert services["template_svc"].all_ids() == []
    assert services["component_svc"].all_ids() == []


@pytest.mark.asyncio
async def test_delete_cascade_mn_reference_does_not_cascade_to_referrer():
    """Deleting a referenced component must NOT delete templates that reference it."""
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    await services["namespace_svc"].create({"id": "ns1", "description": "ns"})
    await services["component_svc"].create(
        {
            "id": "c1",
            "namespace_id": "ns1",
            "component_type": "h",
            "component_name": "n",
            "content": "v",
        }
    )
    await services["template_svc"].create(
        {
            "id": "t1",
            "namespace_id": "ns1",
            "name": "x",
            "components": ["h.n"],
        }
    )

    # Delete just the component (cascade subtree of the component, which has none)
    result = await h.delete_cascade("component", "c1")
    assert result.deleted == {"component": 1}
    assert "t1" in services["template_svc"].all_ids()  # template survives


@pytest.mark.asyncio
async def test_delete_cascade_force_orphan_cleanup():
    """Namespace doc is missing but children exist; cleanup still works."""
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    await services["template_svc"].create(
        {"id": "t1", "namespace_id": "ghost", "name": "x"}
    )
    await services["component_svc"].create(
        {
            "id": "c1",
            "namespace_id": "ghost",
            "component_type": "h",
            "component_name": "n",
            "content": "v",
        }
    )
    # Without flag, cleanup is a no-op (root missing)
    res_noop = await h.delete_cascade("namespace", "ghost")
    assert res_noop.total_deleted == 0
    assert "t1" in services["template_svc"].all_ids()

    # With flag, descendants get cleaned up
    res = await h.delete_cascade("namespace", "ghost", force_orphan_cleanup=True)
    assert res.deleted == {"template": 1, "component": 1}
    assert services["template_svc"].all_ids() == []


@pytest.mark.asyncio
async def test_delete_cascade_children_only_keeps_parent():
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    await services["namespace_svc"].create({"id": "svc", "description": "x"})
    await services["template_svc"].create(
        {"id": "t1", "namespace_id": "svc", "name": "x"}
    )
    res = await h.delete_cascade("namespace", "svc", children_only=True)
    assert res.deleted == {"template": 1}
    assert "svc" in services["namespace_svc"].all_ids()


@pytest.mark.asyncio
async def test_delete_cascade_records_failures_does_not_abort():
    """Best-effort: a single delete failure is logged but cascade continues."""
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)

    await services["namespace_svc"].create({"id": "ns1", "description": "x"})
    await services["template_svc"].create(
        {"id": "t1", "namespace_id": "ns1", "name": "a"}
    )
    await services["template_svc"].create(
        {"id": "t2", "namespace_id": "ns1", "name": "b"}
    )
    services["template_svc"].fail_next_delete("t1")

    res = await h.delete_cascade("namespace", "ns1")
    # t2 succeeds; t1 fails. Parent still attempted.
    assert res.deleted.get("template", 0) == 1
    assert "t1" in res.failed.get("template", [])
    # t1 still in store; t2 gone
    assert services["template_svc"].all_ids() == ["t1"]


@pytest.mark.asyncio
async def test_delete_cascade_restrict_policy_raises_when_children_exist():
    config = HierarchyConfig(
        name="strict_tree",
        root=NodeConfig(
            kind="parent",
            service_ref="p",
            children=[
                NodeConfig(
                    kind="child",
                    service_ref="c",
                    parent_field="parent_id",
                    parent_kind="parent",
                    cascade="restrict",
                )
            ],
        ),
    )
    services = {"p": FakeService(), "c": FakeService()}
    h = HierarchicalUnifiedService(config, services)
    await services["p"].create({"id": "p1"})
    await services["c"].create({"id": "c1", "parent_id": "p1"})

    with pytest.raises(ValueError, match="cascade=restrict"):
        await h.delete_cascade("parent", "p1")


@pytest.mark.asyncio
async def test_subtree_cache_invalidates_on_descendant_delete():
    services = _make_services()
    cache = FakeCache()
    h = HierarchicalUnifiedService(_three_level_config(), services, subtree_cache=cache)

    await services["namespace_svc"].create({"id": "ns1", "description": "x"})
    await services["template_svc"].create(
        {"id": "t1", "namespace_id": "ns1", "name": "a"}
    )

    # Populate cache via read
    await h.get_with_descendants("namespace", "ns1")
    assert any(k.startswith("subtree:namespace:ns1:") for k in cache.keys())

    # Cascade delete must drain those subtree keys
    await h.delete_cascade("namespace", "ns1")
    assert not any(k.startswith("subtree:namespace:ns1:") for k in cache.keys())


@pytest.mark.asyncio
async def test_export_then_import_roundtrip_rewrites_fk_on_descendants():
    """Export a subtree from one parent, change the root's natural key,
    and import — descendants should follow the renamed parent because
    create_with_children re-injects parent_field on each level."""
    config = HierarchyConfig(
        name="rest_client_v2",
        root=NodeConfig(
            kind="service",
            service_ref="service_v2",
            pk_field="name",
            children=[
                NodeConfig(
                    kind="endpoint",
                    service_ref="endpoint_v2",
                    parent_field="parent_id",
                    parent_kind="service",
                ),
            ],
        ),
    )
    services = {
        "service_v2": FakeService(key_field="name"),
        "endpoint_v2": FakeService(),
    }
    h = HierarchicalUnifiedService(config, services)

    # Build an original subtree
    await h.create_with_children(
        "service",
        {"name": "billing", "timeout": 10},
        {
            "endpoint": [
                {"name": "list", "path": "/list"},
                {"name": "create", "path": "/create"},
            ]
        },
    )

    # Export → flatten via the service helper
    exported_tree = await h.get_with_descendants("service", "billing")
    payload = HierarchicalUnifiedService.flatten_for_import(exported_tree)
    assert payload["name"] == "billing"
    assert {e["name"] for e in payload["children"]["endpoint"]} == {"list", "create"}
    # parent_id is in the export, but create_with_children will overwrite
    assert payload["children"]["endpoint"][0]["parent_id"] == "billing"

    # Mutate the root identity and import
    payload["name"] = "billing_clone"
    children = payload.pop("children")
    await h.create_with_children("service", payload, children)

    # The cloned tree exists with rewritten FKs
    cloned = await h.get_with_descendants("service", "billing_clone")
    assert cloned is not None
    assert cloned.entity["name"] == "billing_clone"
    cloned_endpoints = {e.entity["name"]: e.entity["parent_id"] for e in cloned.children["endpoint"]}
    assert cloned_endpoints == {"list": "billing_clone", "create": "billing_clone"}

    # Original is intact
    original = await h.get_with_descendants("service", "billing")
    assert original is not None
    assert {e.entity["name"] for e in original.children["endpoint"]} == {"list", "create"}


@pytest.mark.asyncio
async def test_get_with_descendants_returns_none_for_missing_root():
    services = _make_services()
    h = HierarchicalUnifiedService(_three_level_config(), services)
    assert await h.get_with_descendants("namespace", "missing") is None


@pytest.mark.asyncio
async def test_natural_key_hierarchy_uses_pk_field_for_fk_matching():
    """rest_client_registry-style: service is keyed by `name`, endpoints
    point at the service via `parent_id = service.name`. No ObjectIds
    anywhere in the hierarchy."""

    config = HierarchyConfig(
        name="rest_client_v2",
        root=NodeConfig(
            kind="service",
            service_ref="service_v2",
            pk_field="name",
            children=[
                NodeConfig(
                    kind="endpoint",
                    service_ref="endpoint_v2",
                    parent_field="parent_id",
                    parent_kind="service",
                    cascade="delete",
                )
            ],
        ),
    )
    services = {
        "service_v2": FakeService(key_field="name"),
        "endpoint_v2": FakeService(),
    }
    h = HierarchicalUnifiedService(config, services)

    # Create a service + two endpoints via tree-aware API
    tree = await h.create_with_children(
        "service",
        {"name": "billing", "timeout": 30},
        {
            "endpoint": [
                {"name": "list", "path": "/list", "method": "GET"},
                {"name": "create", "path": "/create", "method": "POST"},
            ]
        },
    )
    assert tree.entity["name"] == "billing"
    # FKs point at the service's *name*, not its ephemeral id
    [ep1, ep2] = tree.children["endpoint"]
    assert ep1.entity["parent_id"] == "billing"
    assert ep2.entity["parent_id"] == "billing"

    # Read back; ensure FK lookup works on natural key
    fetched = await h.get_with_descendants("service", "billing")
    assert fetched is not None
    fetched_names = {e.entity["name"] for e in fetched.children["endpoint"]}
    assert fetched_names == {"list", "create"}

    # Cascade delete by name; endpoints disappear
    res = await h.delete_cascade("service", "billing")
    assert res.deleted == {"endpoint": 2, "service": 1}
    assert services["service_v2"].all_ids() == []
    assert services["endpoint_v2"].all_ids() == []


@pytest.mark.asyncio
async def test_rest_client_v2_hierarchy_yaml_roundtrip(tmp_path):
    """Load the actual rest_client_registry V2 hierarchy YAML and exercise
    end-to-end CRUD against fakes. Proves the YAML schema parses, the tree
    is shaped correctly, and FK matching uses the parent's natural key."""
    import pathlib

    import yaml

    repo_root = pathlib.Path(__file__).resolve().parents[4]
    hierarchy_yaml = (
        repo_root / "config" / "registries" / "rest_client" / "hierarchy.yaml"
    )
    assert hierarchy_yaml.exists(), f"missing {hierarchy_yaml}"
    config = HierarchyConfig(**yaml.safe_load(hierarchy_yaml.read_text())["hierarchy"])

    services = {
        "rest-client-service-v2": FakeService(key_field="name"),
        "rest-client-endpoint-v2": FakeService(),
    }
    h = HierarchicalUnifiedService(config, services)

    # End-to-end: create-with-children → read → cascade delete.
    await h.create_with_children(
        "service",
        {"name": "billing", "timeout": 10},
        {
            "endpoint": [
                {"name": "list", "path": "/list"},
                {"name": "create", "path": "/create"},
            ]
        },
    )
    fetched = await h.get_with_descendants("service", "billing")
    assert fetched is not None
    assert {e.entity["name"] for e in fetched.children["endpoint"]} == {
        "list",
        "create",
    }
    res = await h.delete_cascade("service", "billing")
    assert res.deleted == {"endpoint": 2, "service": 1}


@pytest.mark.asyncio
async def test_prompt_registry_v2_hierarchy_yaml_roundtrip():
    """Load the prompt_registry V2 hierarchy YAML and exercise the
    namespace → (template, component) sibling-children layout, plus the
    M:N reference resolution from template to component."""
    import pathlib

    import yaml

    repo_root = pathlib.Path(__file__).resolve().parents[4]
    base = repo_root / "config" / "registries" / "prompt_registry"
    h_config = HierarchyConfig(
        **yaml.safe_load((base / "hierarchy.yaml").read_text())["hierarchy"]
    )
    template_sc = ServiceConfig(
        **yaml.safe_load((base / "template.yaml").read_text())["service"]
    )
    template_refs = list(template_sc.references)
    assert template_refs, "expected template.yaml to declare M:N references"
    assert template_refs[0].scope_field == "parent_id"

    services = {
        "prompt-namespace-v2": FakeService(key_field="namespace"),
        "prompt-template-v2": FakeService(references=template_refs),
        "prompt-component-v2": FakeService(),
    }
    h = HierarchicalUnifiedService(h_config, services)

    # Build two namespaces with overlapping component type+name to prove
    # that the M:N resolver scopes by parent_id.
    await h.create_with_children(
        "namespace",
        {"namespace": "ns_a", "description": "A"},
        {
            "prompt_template": [
                {
                    "name": "greet",
                    "template": "{{header.welcome}} {{footer.bye}}",
                    "prompt_input": "x",
                    "components": ["header.welcome", "footer.bye"],
                }
            ],
            "prompt_component": [
                {
                    "component_type": "header",
                    "component_name": "welcome",
                    "content": "Hello from A",
                },
                {
                    "component_type": "footer",
                    "component_name": "bye",
                    "content": "Bye from A",
                },
            ],
        },
    )
    await h.create_with_children(
        "namespace",
        {"namespace": "ns_b", "description": "B"},
        {
            "prompt_component": [
                {
                    "component_type": "header",
                    "component_name": "welcome",
                    "content": "Hello from B",
                },
            ],
        },
    )

    # Read namespace A and verify the template resolved components from A,
    # NOT from B (despite identical type+name in B).
    fetched = await h.get_with_descendants("namespace", "ns_a")
    assert fetched is not None
    [template_tree] = fetched.children["prompt_template"]
    resolved = template_tree.references["components"]
    assert len(resolved) == 2
    by_name = {r["component_name"]: r for r in resolved}
    assert by_name["welcome"]["content"] == "Hello from A"  # not "Hello from B"
    assert by_name["welcome"]["parent_id"] == "ns_a"
    assert by_name["bye"]["content"] == "Bye from A"

    # Cascade-delete a referenced component; the template that references
    # it must NOT cascade-delete (M:N is independent of ownership).
    [welcome_a] = await services["prompt-component-v2"].get_entities_by_field_value(
        "parent_id", "ns_a"
    ) and [
        c
        for c in await services["prompt-component-v2"].get_entities_by_field_value(
            "parent_id", "ns_a"
        )
        if c["component_name"] == "welcome"
    ][:1]
    await h.delete_cascade("prompt_component", welcome_a["id"])
    # Template still exists
    surviving_templates = await services["prompt-template-v2"].get_entities_by_field_value(
        "parent_id", "ns_a"
    )
    assert len(surviving_templates) == 1

    # Cascade-delete namespace A: template + remaining component go too,
    # B is untouched.
    res = await h.delete_cascade("namespace", "ns_a")
    assert res.deleted.get("namespace") == 1
    assert res.deleted.get("prompt_template") == 1
    assert res.deleted.get("prompt_component") == 1  # only "bye" remains in A
    # B is intact
    b_components = await services["prompt-component-v2"].get_entities_by_field_value(
        "parent_id", "ns_b"
    )
    assert len(b_components) == 1


@pytest.mark.asyncio
async def test_model_bridge_v2_hierarchy_yaml_roundtrip():
    """Load the model_bridge V2 hierarchy YAML and exercise model →
    deployment cascade against fakes. Both nodes use natural keys
    (model_name / deployment_name) end-to-end — no Mongo ObjectIds."""
    import pathlib

    import yaml

    repo_root = pathlib.Path(__file__).resolve().parents[4]
    hierarchy_yaml = repo_root / "config" / "registries" / "model_bridge" / "hierarchy.yaml"
    assert hierarchy_yaml.exists(), f"missing {hierarchy_yaml}"
    config = HierarchyConfig(**yaml.safe_load(hierarchy_yaml.read_text())["hierarchy"])

    services = {
        "model-bridge-model-v2": FakeService(key_field="model_name"),
        "model-bridge-deployment-v2": FakeService(key_field="deployment_name"),
    }
    h = HierarchicalUnifiedService(config, services)

    await h.create_with_children(
        "model",
        {"model_name": "gpt-4o", "is_active": True},
        {
            "deployment": [
                {
                    "deployment_name": "gpt-4o-prod",
                    "tpm": 1000,
                    "client_identifier": "prod-client",
                    "path_identifier": "/v1/prod",
                },
                {
                    "deployment_name": "gpt-4o-dev",
                    "tpm": 100,
                    "client_identifier": "dev-client",
                    "path_identifier": "/v1/dev",
                },
            ]
        },
    )
    await h.create_with_children(
        "model",
        {"model_name": "claude-opus", "is_active": True},
        {
            "deployment": [
                {
                    "deployment_name": "claude-opus-prod",
                    "tpm": 500,
                    "client_identifier": "prod-client",
                    "path_identifier": "/v1/anthropic-prod",
                }
            ]
        },
    )

    # Read tree for one model — only its own deployments should appear
    fetched = await h.get_with_descendants("model", "gpt-4o")
    assert fetched is not None
    deployment_names = {
        d.entity["deployment_name"] for d in fetched.children["deployment"]
    }
    assert deployment_names == {"gpt-4o-prod", "gpt-4o-dev"}
    # FK is the model's natural-key name
    for d in fetched.children["deployment"]:
        assert d.entity["parent_id"] == "gpt-4o"

    # Cascade-delete one model — the other model and its deployments survive
    res = await h.delete_cascade("model", "gpt-4o")
    assert res.deleted == {"deployment": 2, "model": 1}
    surviving_deployments = (
        await services["model-bridge-deployment-v2"].get_entities_by_field_value(
            "parent_id", "claude-opus"
        )
    )
    assert len(surviving_deployments) == 1
    assert surviving_deployments[0]["deployment_name"] == "claude-opus-prod"


