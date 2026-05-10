"""
Custom Metric Store System.

This module provides a comprehensive metric store system for collecting,
aggregating, and computing metrics with support for sliding windows,
derived metrics, and multiple storage backends.

Key Features:
- Raw and final metric stores
- Sliding window support
- Derived metrics with dependency resolution
- Multiple algorithms (EWMA, Welford, T-digest)
- In-memory and Redis backends
- Self-monitoring and observability

Example Usage:
    ```python
    from common_utils.work_in_progress.kpi_store import KPIStoreFactory, KPIDefinition

    # Create a KPI store
    kpi_store = KPIStoreFactory.create_in_memory_kpi_store()

    # Define a metric
    definition = KPIDefinition(
        metric_id="http_requests_total",
        metric_type=KPIStoreType.COUNTER,
        algorithm=Algorithm.COUNTER,
        # ... other configuration
    )

    # Register and use the metric
    await kpi_store.register_metric(definition)
    await kpi_store.record_metric("http_requests_total", 1.0)

    # Get current value
    value = await kpi_store.get_metric_value("http_requests_total")
    print(f"Total requests: {value.value}")
    ```
"""

from .algorithms import (
    CounterAlgorithm,
    EWMAAlgorithm,
    GaugeAlgorithm,
    SimpleAverageAlgorithm,
    WelfordAlgorithm,
    create_algorithm,
)
from .derived_metrics import DerivedMetricsManager
from .enums import (
    AggregationFunction,
    Algorithm,
    CleanupStrategy,
    KPIStatus,
    KPIStoreType,
    StoreBackend,
    UpdateStrategy,
    UpdateTrigger,
)
from .factory import KPIStoreFactory, create_kpi_store, create_test_kpi_store
from .integration import (
    KPIStoreIntegration,
    create_kpi_store_for_module,
    get_kpi_store_from_app_container,
    setup_kpi_store_integration,
)
from .interfaces import (
    IFinalStore,
    IKPIAlgorithm,
    IKPIStore,
    IRawStore,
)
from .kpi_store import KPIStore
from .models import (
    BatchResult,
    CircuitBreakerConfig,
    DerivedKPIDefinition,
    FinalStoreConfig,
    KPIDefinition,
    KPIPoint,
    KPIStats,
    KPIStoreConfig,
    KPIValue,
    RawStoreConfig,
    RetentionPolicy,
    SlidingWindowConfig,
    TimeWindow,
)
from .monitoring import KPIStoreHealthChecker, KPIStoreMetrics
from .stores import (
    InMemoryFinalStore,
    InMemoryRawStore,
    RedisFinalStore,
    RedisRawStore,
)

__all__ = [
    # Enums
    "KPIStoreType",
    "UpdateStrategy",
    "Algorithm",
    "StoreBackend",
    "CleanupStrategy",
    "UpdateTrigger",
    "AggregationFunction",
    "KPIStatus",
    # Models
    "KPIPoint",
    "TimeWindow",
    "RetentionPolicy",
    "SlidingWindowConfig",
    "RawStoreConfig",
    "FinalStoreConfig",
    "KPIDefinition",
    "DerivedKPIDefinition",
    "KPIStoreConfig",
    "BatchResult",
    "KPIValue",
    "KPIStats",
    "CircuitBreakerConfig",
    # Interfaces
    "IRawStore",
    "IFinalStore",
    "IKPIStore",
    "IKPIAlgorithm",
    # Algorithms
    "EWMAAlgorithm",
    "WelfordAlgorithm",
    "SimpleAverageAlgorithm",
    "CounterAlgorithm",
    "GaugeAlgorithm",
    "create_algorithm",
    # Stores
    "InMemoryRawStore",
    "RedisRawStore",
    "InMemoryFinalStore",
    "RedisFinalStore",
    # Core Components
    "DerivedMetricsManager",
    "KPIStore",
    "KPIStoreFactory",
    # Factory Functions
    "create_kpi_store",
    "create_test_kpi_store",
    # Integration
    "KPIStoreIntegration",
    "setup_kpi_store_integration",
    "get_kpi_store_from_app_container",
    "create_kpi_store_for_module",
    # Monitoring
    "KPIStoreMetrics",
    "KPIStoreHealthChecker",
]

# Version information
__version__ = "1.0.0"
__author__ = "modelswitch Team"
__description__ = "Custom KPI store system with sliding windows and derived KPIs"
