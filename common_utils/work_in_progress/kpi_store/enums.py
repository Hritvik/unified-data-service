"""
Enums for the KPI store system.
"""

from enum import Enum


class Algorithm(str, Enum):
    """Computation algorithms for KPIs."""

    COUNTER = "counter"
    GAUGE = "gauge"
    SIMPLE_AVERAGE = "simple_average"
    EWMA = "ewma"
    WELFORD = "welford"
    T_DIGEST = "t_digest"
    CUSTOM = "custom"


class KPIStoreType(str, Enum):
    """Types of KPIs supported by the KPI store."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class StoreBackend(str, Enum):
    """Storage backend types."""

    IN_MEMORY = "in_memory"
    REDIS = "redis"


class CleanupStrategy(str, Enum):
    """Strategies for cleaning up expired data."""

    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    HYBRID = "hybrid"
    NONE = "none"


class UpdateStrategy(str, Enum):
    """Strategies for updating KPI values."""

    IMMEDIATE = "immediate"
    LAZY = "lazy"
    BATCHED = "batched"
    SCHEDULED = "scheduled"


class UpdateTrigger(str, Enum):
    """Triggers for KPI updates."""

    ON_RECORD = "on_record"
    ON_READ = "on_read"
    TIME_BASED = "time_based"
    MANUAL = "manual"


class AggregationFunction(str, Enum):
    """Functions for aggregating KPI values."""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


class KPIStatus(str, Enum):
    """Status of a KPI."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"
