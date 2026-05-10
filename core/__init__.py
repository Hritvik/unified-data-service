"""Core unified data service modules."""

from .interfaces import (
    IDataSource,
    IUnifiedService,
    DataSourceQuery,
    BulkOperationResult,
    PaginatedResult,
    ServiceConfig,
    CacheStrategy,
    ReferenceConfig,
    NodeConfig,
    HierarchyConfig,
    CustomEndpointConfig,
    ControllerConfig,
)
from .service import UnifiedDataService

__all__ = [
    "IDataSource",
    "IUnifiedService", 
    "DataSourceQuery",
    "BulkOperationResult",
    "PaginatedResult",
    "ServiceConfig",
    "CacheStrategy",
    "ReferenceConfig",
    "NodeConfig",
    "HierarchyConfig",
    "CustomEndpointConfig",
    "ControllerConfig",
    "UnifiedDataService",
]
