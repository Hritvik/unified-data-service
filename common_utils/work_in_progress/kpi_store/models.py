"""
Data models for the KPI store system.
"""

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import (
    Algorithm,
    CleanupStrategy,
    KPIStatus,
    KPIStoreType,
    StoreBackend,
    UpdateStrategy,
    UpdateTrigger,
)


class KPIPoint(BaseModel):
    """A single KPI data point with timestamp and value."""

    timestamp: float = Field(
        default_factory=time.time, description="Timestamp of the KPI"
    )
    value: float = Field(description="KPI value")


class TimeWindow(BaseModel):
    """Time window configuration for KPI aggregation."""

    duration_seconds: int = Field(description="Duration of the time window in seconds")
    name: str = Field(description="Name of the time window (e.g., '1m', '5m', '1h')")


class RetentionPolicy(BaseModel):
    """Retention policy for KPI data."""

    ttl_seconds: Optional[int] = Field(None, description="Time to live in seconds")
    max_samples: Optional[int] = Field(
        None, description="Maximum number of samples to retain"
    )
    max_size_bytes: Optional[int] = Field(None, description="Maximum size in bytes")


class SlidingWindowConfig(BaseModel):
    """Configuration for sliding window operations."""

    window_size_seconds: int = Field(
        description="Size of the sliding window in seconds"
    )
    slide_interval_seconds: Optional[int] = Field(
        None, description="Interval at which the window slides"
    )
    max_samples: Optional[int] = Field(
        None, description="Maximum number of samples in the window"
    )
    cleanup_strategy: CleanupStrategy = Field(
        CleanupStrategy.HYBRID, description="Strategy for cleaning up expired data"
    )


class RawStoreConfig(BaseModel):
    """Configuration for raw KPI storage."""

    backend: StoreBackend = Field(
        StoreBackend.IN_MEMORY, description="Storage backend to use"
    )
    sliding_window: Optional[SlidingWindowConfig] = Field(
        None, description="Sliding window configuration"
    )
    retention_policy: Optional[RetentionPolicy] = Field(
        None, description="Retention policy for raw data"
    )
    key_prefix: Optional[str] = Field(None, description="Key prefix for Redis storage")


class FinalStoreConfig(BaseModel):
    """Configuration for final (aggregated) KPI storage."""

    backend: StoreBackend = Field(
        StoreBackend.IN_MEMORY, description="Storage backend to use"
    )
    update_strategy: UpdateStrategy = Field(
        UpdateStrategy.IMMEDIATE, description="Strategy for updating values"
    )
    update_trigger: UpdateTrigger = Field(
        UpdateTrigger.ON_RECORD, description="Trigger for updates"
    )
    key_prefix: Optional[str] = Field(None, description="Key prefix for Redis storage")
    cache_ttl_seconds: Optional[int] = Field(None, description="Cache TTL in seconds")


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker pattern."""

    failure_threshold: int = Field(
        5, description="Number of failures before opening circuit"
    )
    recovery_threshold: int = Field(
        3, description="Number of successes to close circuit"
    )
    timeout_duration_seconds: int = Field(60, description="Timeout duration in seconds")


class KPIDefinition(BaseModel):
    """Definition of a KPI to be stored."""

    metric_id: str = Field(description="Unique identifier for the KPI")
    metric_type: KPIStoreType = Field(description="Type of the KPI")
    algorithm: Algorithm = Field(description="Algorithm to use for computation")
    description: Optional[str] = Field(None, description="Description of the KPI")
    raw_store_config: Optional[RawStoreConfig] = Field(
        None, description="Raw store configuration"
    )
    final_store_config: Optional[FinalStoreConfig] = Field(
        None, description="Final store configuration"
    )
    aggregation_windows: Optional[List[TimeWindow]] = Field(
        None, description="Time windows for aggregation"
    )
    tags: Optional[Dict[str, Any]] = Field(
        None, description="Tags/metadata for the KPI"
    )
    circuit_breaker_config: Optional[CircuitBreakerConfig] = Field(
        None, description="Circuit breaker configuration"
    )
    status: KPIStatus = Field(KPIStatus.ACTIVE, description="Status of the KPI")


class DerivedKPIDefinition(BaseModel):
    """Definition of a derived KPI computed from other KPIs."""

    metric_id: str = Field(description="Unique identifier for the derived KPI")
    dependencies: List[str] = Field(description="List of KPI IDs this KPI depends on")
    computation_function_name: str = Field(
        description="Name of the function to compute the derived KPI"
    )
    description: Optional[str] = Field(
        None, description="Description of the derived KPI"
    )
    final_store_config: Optional[FinalStoreConfig] = Field(
        None, description="Final store configuration"
    )
    tags: Optional[Dict[str, Any]] = Field(
        None, description="Tags/metadata for the KPI"
    )
    status: KPIStatus = Field(KPIStatus.ACTIVE, description="Status of the KPI")


class KPIValue(BaseModel):
    """A computed KPI value."""

    metric_id: str = Field(description="KPI identifier")
    value: float = Field(description="Computed value")
    timestamp: float = Field(
        default_factory=time.time, description="Timestamp of computation"
    )
    window_name: Optional[str] = Field(
        None, description="Time window name if applicable"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class KPIStats(BaseModel):
    """Statistics about a KPI."""

    metric_id: str = Field(description="KPI identifier")
    sample_count: int = Field(0, description="Number of samples")
    last_update: Optional[float] = Field(None, description="Last update timestamp")
    min_value: Optional[float] = Field(None, description="Minimum value")
    max_value: Optional[float] = Field(None, description="Maximum value")
    avg_value: Optional[float] = Field(None, description="Average value")


class BatchResult(BaseModel):
    """Result of a batch operation."""

    total_processed: int = Field(0, description="Total items processed")
    successful: int = Field(0, description="Number of successful operations")
    failed: int = Field(0, description="Number of failed operations")
    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )
    processing_time_seconds: float = Field(
        0.0, description="Processing time in seconds"
    )


class KPIStoreConfig(BaseModel):
    """Configuration for the KPI store system."""

    default_raw_backend: StoreBackend = Field(
        StoreBackend.IN_MEMORY, description="Default backend for raw storage"
    )
    default_final_backend: StoreBackend = Field(
        StoreBackend.IN_MEMORY, description="Default backend for final storage"
    )
    enable_parallel_derived_computation: bool = Field(
        True, description="Enable parallel computation of derived KPIs"
    )
    batch_size: int = Field(1000, description="Batch size for operations")
    max_memory_usage_mb: Optional[int] = Field(
        None, description="Maximum memory usage in MB"
    )
    cleanup_interval_seconds: int = Field(
        300, description="Cleanup interval in seconds"
    )
    background_cleanup_enabled: bool = Field(
        True, description="Enable background cleanup"
    )
    redis_key_prefix: str = Field("modelswitch:kpi:", description="Redis key prefix")
    redis_use_case: Optional[str] = Field(None, description="Redis use case identifier")
