"""Unified data service infrastructure.

This package provides a unified architecture for data services that eliminates
the need for repetitive CacheMixin + Repository + Service patterns.

The UnifiedDataService now includes both CRUD operations and business logic
optimization in a single class for maximum simplicity and performance.
"""

from .interfaces import IDataSource, IUnifiedService, PaginatedResult
from .service import UnifiedDataService

__all__ = [
    "IDataSource",
    "IUnifiedService",
    "PaginatedResult",
    "UnifiedDataService",
]
