"""Interfaces for the unified data service architecture.

This module defines the core interfaces that enable pluggable data sources
and unified service operations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")  # Entity type
K = TypeVar("K")  # Key type


class DataSourceQuery(BaseModel):
    """Query parameters for data source operations."""

    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    skip: Optional[int] = None
    sort_by: Optional[str] = None
    sort_order: int = 1  # 1 for ascending, -1 for descending


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""

    success_count: int = 0
    error_count: int = 0
    total_count: int = 0
    errors: List[str] = []

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count


class PaginatedResult(BaseModel):
    """Paginated result with metadata."""

    items: List[Any] = []
    total: int = 0
    limit: int = 0
    skip: int = 0
    has_more: bool = False


class IDataSource(ABC, Generic[T, K]):
    """Interface for data sources (MongoDB, API, File, etc.)."""

    @abstractmethod
    async def get_by_id(self, id: K) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, query: Optional[DataSourceQuery] = None) -> List[T]:
        """Get all entities matching query."""
        pass

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    async def update(self, id: K, data: Dict[str, Any]) -> Optional[T]:
        """Update entity by ID."""
        pass

    @abstractmethod
    async def delete(self, id: K) -> bool:
        """Delete entity by ID."""
        pass

    @abstractmethod
    async def exists(self, id: K) -> bool:
        """Check if entity exists."""
        pass

    @abstractmethod
    async def count(self, query: Optional[DataSourceQuery] = None) -> int:
        """Count entities matching query."""
        pass

    # Bulk Operations
    @abstractmethod
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> BulkOperationResult:
        """Create multiple entities."""
        pass

    @abstractmethod
    async def bulk_update(
        self, updates: Dict[K, Dict[str, Any]]
    ) -> BulkOperationResult:
        """Update multiple entities."""
        pass

    @abstractmethod
    async def bulk_delete(self, ids: List[K]) -> BulkOperationResult:
        """Delete multiple entities."""
        pass

    @abstractmethod
    async def bulk_get(self, ids: List[K]) -> Dict[K, Optional[T]]:
        """Get multiple entities by IDs."""
        pass

    @abstractmethod
    async def delete_all(self) -> int:
        """Delete all entities from the data source."""
        pass

    # Advanced Operations
    @abstractmethod
    async def find(self, query: DataSourceQuery) -> List[T]:
        """Find entities by complex query."""
        pass

    @abstractmethod
    async def find_one(self, query: DataSourceQuery) -> Optional[T]:
        """Find one entity by query."""
        pass

    @abstractmethod
    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        pass

    @abstractmethod
    async def distinct(
        self, field: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Return distinct values of `field`, optionally constrained by
        a filter expression."""
        pass

    # Metadata
    @abstractmethod
    def get_entity_type(self) -> type[T]:
        """Get the entity type this data source handles."""
        pass

    @abstractmethod
    def get_key_type(self) -> type[K]:
        """Get the key type this data source uses."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check data source health."""
        pass


class CacheStrategy(str, Enum):
    """Cache strategy enumeration."""

    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    CACHE_ASIDE = "cache_aside"
    READ_THROUGH = "read_through"


class IUnifiedService(ABC, Generic[T, K]):
    """Interface for unified data services."""

    # Basic CRUD Operations
    @abstractmethod
    async def get_by_id(self, id: K) -> Optional[T]:
        """Get entity by ID with caching."""
        pass

    @abstractmethod
    async def get_all(self, query: Optional[DataSourceQuery] = None) -> List[T]:
        """Get all entities with caching."""
        pass

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity with cache invalidation."""
        pass

    @abstractmethod
    async def update(self, id: K, data: Dict[str, Any]) -> Optional[T]:
        """Update entity with cache invalidation."""
        pass

    @abstractmethod
    async def delete(self, id: K) -> bool:
        """Delete entity with cache invalidation."""
        pass

    @abstractmethod
    async def exists(self, id: K) -> bool:
        """Check if entity exists without fetching the full document."""
        pass

    # Bulk Operations
    @abstractmethod
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> BulkOperationResult:
        """Bulk create with cache warming."""
        pass

    @abstractmethod
    async def bulk_update(
        self, updates: Dict[K, Dict[str, Any]]
    ) -> BulkOperationResult:
        """Bulk update with cache invalidation."""
        pass

    @abstractmethod
    async def bulk_delete(self, ids: List[K]) -> BulkOperationResult:
        """Bulk delete with cache invalidation."""
        pass

    # Cache Management
    @abstractmethod
    async def warm_cache(self) -> int:
        """Warm cache with all data from source."""
        pass

    @abstractmethod
    async def invalidate_cache(self, keys: Optional[List[str]] = None) -> None:
        """Invalidate cache (all or specific keys)."""
        pass

    @abstractmethod
    async def refresh_cache(self) -> int:
        """Refresh cache by clearing and reloading.

        Returns:
            Number of items cached after refresh.
        """
        pass

    # Paginated Operations
    @abstractmethod
    async def get_paginated(
        self, query: Optional[DataSourceQuery] = None
    ) -> PaginatedResult:
        """Get entities with pagination metadata. Applies default limit if none specified."""
        pass

    @abstractmethod
    async def search_paginated(self, query: DataSourceQuery) -> PaginatedResult:
        """Search entities with pagination metadata. Applies default limit if none specified."""
        pass

    # Advanced Operations
    @abstractmethod
    async def search(self, query: DataSourceQuery) -> List[T]:
        """Search entities with caching."""
        pass

    @abstractmethod
    async def count(self, query: Optional[DataSourceQuery] = None) -> int:
        """Count entities with caching."""
        pass

    @abstractmethod
    async def distinct(
        self, field: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Return distinct values of `field` across the collection."""
        pass

    # Statistics and Monitoring
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        pass

    @abstractmethod
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache configuration and capabilities."""
        pass

    @abstractmethod
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get overall service statistics."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check service health (cache + data source)."""
        pass


class ServiceConfig(BaseModel):
    """Configuration for unified data services."""

    name: str
    entity_type: str
    key_type: str = "str"

    # Data Source Configuration
    data_source: Dict[str, Any]

    # Cache Configuration
    cache_backend: str = "redis"  # "redis" or "in_memory"
    cache_ttl: Optional[int] = 300  # 5 minutes default
    cache_key_prefix: str = ""

    # Strategy Configuration
    cache_strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH
    enable_bulk_operations: bool = True
    enable_cache_warming: bool = True

    # Performance Configuration
    max_bulk_size: int = 1000
    query_timeout_seconds: int = 30

    # Upsert configuration — fields to match on for bulk_upsert
    # e.g. ["category_id"] or ["sub_category_id", "scenario_identifier"]
    upsert_fields: List[str] = []

    # Pagination defaults (used by get_paginated / search_paginated)
    default_limit: int = 100
    max_limit: int = 1000

    # Event Configuration
    enable_event_invalidation: bool = True
    event_service_name: Optional[str] = None

    # Business logic configuration
    business_logic_class: Optional[
        str
    ] = None  # e.g., "ticket_resolution.services.ic_subcategory_business.ICSubcategoryBusinessLogic"

    # Lookup optimization configuration
    lookup_optimization: Optional[Dict[str, Any]] = None
    # Example:
    # {
    #   "enabled": true,
    #   "builder_method": "_build_lookup_structures",
    #   "rebuild_on": ["create", "update", "delete", "bulk_update", "bulk_delete"]
    # }

    # M:N cross-references resolved at read time by the hierarchical layer.
    # Independent of ownership tree; deleting a referenced entity does not
    # cascade-delete the referrer.
    references: List["ReferenceConfig"] = []

    # Controller configuration for auto-generated REST endpoints
    controller: Optional["ControllerConfig"] = None


CascadePolicy = Literal["delete", "restrict", "detach"]


class ReferenceConfig(BaseModel):
    """M:N cross-reference between two services. Lives on ServiceConfig.references.

    Resolved at read time in HierarchicalUnifiedService.get_with_descendants.
    Resolver options:
      - "id": field holds list of target IDs
      - "type.name": field holds list of "{type}.{name}" strings; the target
        service is queried by component_type + component_name composite
      - dotted-path: arbitrary attribute path on the entity

    `scope_field` (optional) names a field present on BOTH the referrer and
    the target — when set, the lookup is additionally constrained to
    `target.<scope_field> == referrer.<scope_field>`. Use this to keep M:N
    references namespace-scoped (e.g., a template only references
    components living under the same `parent_id`).
    """

    name: str
    field: str
    target_service: str
    resolver: str = "id"
    scope_field: Optional[str] = None


class NodeConfig(BaseModel):
    """One node in a HierarchyConfig tree."""

    kind: str
    service_ref: str
    parent_field: Optional[str] = None
    parent_kind: Optional[str] = None
    # Name of the field on this entity that serves as its primary key for
    # FK matching (i.e., the value other nodes' `parent_field` columns hold).
    # Defaults to "id" (Beanie/Mongo convention). Set to a natural-key field
    # like "name" when other nodes reference this one by that field instead.
    pk_field: str = "id"
    cascade: CascadePolicy = "delete"
    unique_within_parent: List[str] = []
    children: List["NodeConfig"] = []


class HierarchyConfig(BaseModel):
    """Declarative configuration of a parent-child entity tree.

    Each node names a previously-registered ServiceConfig (by service_ref).
    The hierarchical layer composes those services without subclassing them.
    """

    name: str
    root: NodeConfig
    subtree_cache_ttl_seconds: int = 60
    subtree_cache_key_prefix: str = "subtree"


# Forward-ref resolution for self-referential NodeConfig.children and the
# string-typed references field on ServiceConfig.



class CustomEndpointConfig(BaseModel):
    """Configuration for custom business endpoints."""

    method: str  # "GET", "POST", etc.
    path: str  # "/categories/{category_id}/subcategories"
    service_method: str  # "business.get_subcategories_for_category"
    response_model: Optional[str] = None
    request_model: Optional[str] = None
    description: Optional[str] = None


class ControllerConfig(BaseModel):
    """Configuration for auto-generated controllers."""

    base_path: str
    custom_endpoints: List[CustomEndpointConfig] = []
    middleware: List[str] = []
    # When true, every successful handler return is wrapped in a
    # ``{"success": true, "data": <return>, "message": "..."}`` envelope —
    # matching the convention the hand-rolled rest_client / prompt_registry
    # / model_bridge controllers used. Default false so existing
    # ticket_resolution YAMLs (already on UnifiedController) keep returning
    # raw bodies.
    response_envelope: bool = False


# Forward-ref resolution
NodeConfig.model_rebuild()
ServiceConfig.model_rebuild()
HierarchyConfig.model_rebuild()
