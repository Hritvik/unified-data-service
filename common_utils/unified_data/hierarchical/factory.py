"""Factory for HierarchicalUnifiedService.

Resolves NodeConfig.service_ref names against ServiceFactory's registry
and constructs a wired HierarchicalUnifiedService. Per-level services must
be registered via ServiceFactory.create_service before calling
create_hierarchy.
"""

from __future__ import annotations

from typing import Dict, Optional

from common_utils.cache import ICacheRepository
from common_utils.logger import get_logger

from ..factories.service_factory import ServiceFactory
from ..interfaces import HierarchyConfig, NodeConfig
from ..service import UnifiedDataService
from .service import HierarchicalUnifiedService

logger = get_logger(__name__)


class HierarchicalServiceFactory:
    """Factory for hierarchical (tree-aware) services.

    Stateless utility — does not maintain its own registry. The composed
    UnifiedDataService instances are looked up from
    ServiceFactory._service_registry by their `service_ref` names.
    """

    @classmethod
    def create_hierarchy(
        cls,
        config: HierarchyConfig,
        subtree_cache: Optional[ICacheRepository] = None,
    ) -> HierarchicalUnifiedService:
        """Build a HierarchicalUnifiedService from a HierarchyConfig.

        Args:
            config: Tree configuration declaring node kinds and parent links.
            subtree_cache: Optional cache repository for subtree views. If
                None, subtree caching is disabled (per-entity caches still
                operate inside each composed UnifiedDataService).

        Raises:
            ValueError: If a referenced service is not registered.
        """
        services = cls._collect_services(config.root, {})
        return HierarchicalUnifiedService(
            config=config, services=services, subtree_cache=subtree_cache
        )

    @classmethod
    def _collect_services(
        cls, node: NodeConfig, acc: Dict[str, UnifiedDataService]
    ) -> Dict[str, UnifiedDataService]:
        service = ServiceFactory.get_service(node.service_ref)
        if service is None:
            raise ValueError(
                f"Service '{node.service_ref}' (for node kind '{node.kind}') "
                f"is not registered. Call ServiceFactory.create_service first."
            )
        acc[node.service_ref] = service
        for child in node.children:
            cls._collect_services(child, acc)
        return acc
