"""
Core KPI store implementation.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from .algorithms import create_algorithm
from .derived_metrics import DerivedMetricsManager
from .enums import StoreBackend
from .interfaces import IFinalStore, IKPIStore, IKPIAlgorithm, IRawStore
from .models import (
    BatchResult,
    DerivedKPIDefinition,
    KPIDefinition,
    KPIPoint,
    KPIStoreConfig,
    KPIValue,
)
from .monitoring import KPIStoreMetrics
from .stores import (
    InMemoryFinalStore,
    InMemoryRawStore,
    RedisFinalStore,
    RedisRawStore,
)

logger = get_logger(__name__)


class KPIStore(IKPIStore):
    """Main KPI store implementation."""

    def __init__(
        self, config: KPIStoreConfig, redis_client: Optional[RedisClient] = None
    ) -> None:
        """
        Initialize KPI store.

        Args:
            config: KPI store configuration
            redis_client: Redis client (required for Redis backends)
        """
        self.config = config
        self.redis_client = redis_client
        self.logger = logger

        # Storage for raw and final stores per metric
        self.raw_stores: Dict[str, IRawStore] = {}
        self.final_stores: Dict[str, IFinalStore] = {}

        # Metric definitions
        self.metric_definitions: Dict[str, KPIDefinition] = {}
        self.derived_metrics_manager = DerivedMetricsManager(
            self, enable_parallel=config.enable_parallel_derived_computation
        )

        # Algorithms cache
        self.algorithms: Dict[str, IKPIAlgorithm] = {}

        # Monitoring
        self.metrics = KPIStoreMetrics()

        # Statistics
        self._stats = {
            "start_time": time.time(),
            "total_metrics_recorded": 0,
            "total_computations": 0,
            "errors": 0,
        }

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Start background cleanup if enabled
        if config.background_cleanup_enabled:
            self._start_background_cleanup()

    def _create_raw_store(self, metric_id: str, config: KPIDefinition) -> IRawStore:
        """Create a raw store for a metric."""
        backend = (
            config.raw_store_config.backend
            if config.raw_store_config
            else self.config.default_raw_backend
        )

        if backend == StoreBackend.REDIS:
            if not self.redis_client:
                raise ValueError("Redis client required for Redis backend")
            key_prefix = (
                config.raw_store_config.key_prefix
                if config.raw_store_config and config.raw_store_config.key_prefix
                else f"{self.config.redis_key_prefix}raw:"
            )
            ttl = (
                config.raw_store_config.retention_policy.ttl_seconds
                if config.raw_store_config
                and config.raw_store_config.retention_policy
                and config.raw_store_config.retention_policy.ttl_seconds
                else None
            )
            return RedisRawStore(
                self.redis_client, key_prefix=key_prefix, ttl_seconds=ttl
            )
        else:
            max_samples = (
                config.raw_store_config.sliding_window.max_samples
                if config.raw_store_config
                and config.raw_store_config.sliding_window
                and config.raw_store_config.sliding_window.max_samples
                else None
            )
            ttl = (
                config.raw_store_config.retention_policy.ttl_seconds
                if config.raw_store_config
                and config.raw_store_config.retention_policy
                and config.raw_store_config.retention_policy.ttl_seconds
                else None
            )
            return InMemoryRawStore(max_samples=max_samples, ttl_seconds=ttl)

    def _create_final_store(self, metric_id: str, config: KPIDefinition) -> IFinalStore:
        """Create a final store for a metric."""
        backend = (
            config.final_store_config.backend
            if config.final_store_config
            else self.config.default_final_backend
        )

        if backend == StoreBackend.REDIS:
            if not self.redis_client:
                raise ValueError("Redis client required for Redis backend")
            key_prefix = (
                config.final_store_config.key_prefix
                if config.final_store_config and config.final_store_config.key_prefix
                else f"{self.config.redis_key_prefix}final:"
            )
            ttl = (
                config.final_store_config.cache_ttl_seconds
                if config.final_store_config
                and config.final_store_config.cache_ttl_seconds
                else None
            )
            return RedisFinalStore(
                self.redis_client, key_prefix=key_prefix, ttl_seconds=ttl
            )
        else:
            return InMemoryFinalStore()

    async def register_metric(self, definition: KPIDefinition) -> None:
        """Register a metric definition."""
        try:
            self.metric_definitions[definition.metric_id] = definition

            # Create stores
            self.raw_stores[definition.metric_id] = self._create_raw_store(
                definition.metric_id, definition
            )
            self.final_stores[definition.metric_id] = self._create_final_store(
                definition.metric_id, definition
            )

            # Create algorithm instance
            algorithm_key = f"{definition.metric_id}_{definition.algorithm.value}"
            if algorithm_key not in self.algorithms:
                algorithm_params = definition.tags or {}
                self.algorithms[algorithm_key] = create_algorithm(
                    definition.algorithm, algorithm_params
                )

            await self.metrics.record_operation("register_metric", success=True)
            self.logger.info(f"Registered metric: {definition.metric_id}")

        except Exception as e:
            self._stats["errors"] += 1
            await self.metrics.record_operation("register_metric", success=False)
            self.logger.error(f"Error registering metric {definition.metric_id}: {e}")
            raise

    async def register_derived_metric(self, definition: DerivedKPIDefinition) -> None:
        """Register a derived metric definition."""
        try:
            self.derived_metrics_manager.register_derived_metric(definition)
            await self.metrics.record_operation("register_derived_metric", success=True)
            self.logger.info(f"Registered derived metric: {definition.metric_id}")
        except Exception as e:
            self._stats["errors"] += 1
            await self.metrics.record_operation(
                "register_derived_metric", success=False
            )
            self.logger.error(
                f"Error registering derived metric {definition.metric_id}: {e}"
            )
            raise

    async def record_metric(
        self, metric_id: str, value: float, timestamp: Optional[float] = None
    ) -> None:
        """Record a metric value."""
        start_time = time.time()
        try:
            if metric_id not in self.metric_definitions:
                raise ValueError(f"Metric not registered: {metric_id}")

            definition = self.metric_definitions[metric_id]
            raw_store = self.raw_stores[metric_id]

            # Create metric point
            point = KPIPoint(value=value, timestamp=timestamp or time.time())

            # Add to raw store
            await raw_store.add_sample(metric_id, point)

            # Compute and store final value
            await self._compute_and_store(metric_id, definition)

            # Compute derived metrics that depend on this one
            await self._update_derived_metrics(metric_id)

            self._stats["total_metrics_recorded"] += 1
            await self.metrics.record_sample(metric_id)
            await self.metrics.record_operation(
                "record_metric", success=True, duration=time.time() - start_time
            )

        except Exception as e:
            self._stats["errors"] += 1
            await self.metrics.record_operation(
                "record_metric", success=False, duration=time.time() - start_time
            )
            self.logger.error(f"Error recording metric {metric_id}: {e}")
            raise

    async def _compute_and_store(
        self, metric_id: str, definition: KPIDefinition
    ) -> None:
        """Compute metric value and store in final store."""
        try:
            raw_store = self.raw_stores[metric_id]
            final_store = self.final_stores[metric_id]

            # Get samples
            samples = await raw_store.get_samples(metric_id)

            # Get algorithm
            algorithm_key = f"{metric_id}_{definition.algorithm.value}"
            algorithm = self.algorithms[algorithm_key]

            # Get previous value
            previous_value_obj = await final_store.get_metric_value(metric_id)
            previous_value = previous_value_obj.value if previous_value_obj else None

            # Compute new value
            computed_value = await algorithm.compute(samples, previous_value)

            # Store in final store
            metric_value = KPIValue(
                metric_id=metric_id,
                value=computed_value,
                timestamp=time.time(),
            )
            await final_store.set_metric_value(metric_id, metric_value)

            self._stats["total_computations"] += 1
            await self.metrics.record_computation(
                metric_id, definition.algorithm.value, 0.0, success=True
            )

        except Exception as e:
            self.logger.error(f"Error computing metric {metric_id}: {e}")
            raise

    async def _update_derived_metrics(self, base_metric_id: str) -> None:
        """Update derived metrics that depend on the given base metric."""
        try:
            # Find derived metrics that depend on this metric
            derived_metrics = self.derived_metrics_manager.list_derived_metrics()
            for derived_id in derived_metrics:
                definition = self.derived_metrics_manager.get_derived_metric_definition(
                    derived_id
                )
                if definition and base_metric_id in definition.dependencies:
                    # Compute and store derived metric
                    computed_value = (
                        await self.derived_metrics_manager.compute_derived_metric(
                            derived_id
                        )
                    )
                    if computed_value:
                        # Store in final store (create one if needed)
                        if derived_id not in self.final_stores:
                            # Use default final store
                            if self.config.default_final_backend == StoreBackend.REDIS:
                                if not self.redis_client:
                                    continue
                                self.final_stores[derived_id] = RedisFinalStore(
                                    self.redis_client,
                                    key_prefix=f"{self.config.redis_key_prefix}final:",
                                )
                            else:
                                self.final_stores[derived_id] = InMemoryFinalStore()

                        await self.final_stores[derived_id].set_metric_value(
                            derived_id, computed_value
                        )

        except Exception as e:
            self.logger.warning(
                f"Error updating derived metrics for {base_metric_id}: {e}"
            )

    async def record_metrics_batch(self, metrics: Dict[str, Any]) -> BatchResult:
        """Record multiple metrics in a batch."""
        start_time = time.time()
        result = BatchResult(total_processed=0, successful=0, failed=0)

        for metric_id, value in metrics.items():
            result.total_processed += 1
            try:
                if isinstance(value, list):
                    # Multiple points
                    for point in value:
                        if isinstance(point, KPIPoint):
                            await self.record_metric(
                                metric_id, point.value, point.timestamp
                            )
                        else:
                            await self.record_metric(metric_id, float(point))
                else:
                    await self.record_metric(metric_id, float(value))
                result.successful += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"{metric_id}: {str(e)}")

        result.processing_time_seconds = time.time() - start_time
        return result

    async def get_metric_value(
        self, metric_id: str, window_name: Optional[str] = None
    ) -> Optional[KPIValue]:
        """Get the current value of a metric."""
        try:
            # Check if it's a derived metric
            if metric_id in self.derived_metrics_manager.list_derived_metrics():
                return await self.derived_metrics_manager.compute_derived_metric(
                    metric_id
                )

            # Regular metric
            if metric_id not in self.final_stores:
                return None

            final_store = self.final_stores[metric_id]
            return await final_store.get_metric_value(metric_id, window_name)

        except Exception as e:
            self.logger.error(f"Error getting metric value {metric_id}: {e}")
            return None

    async def list_metrics(self) -> List[str]:
        """List all registered metrics."""
        base_metrics = list(self.metric_definitions.keys())
        derived_metrics = self.derived_metrics_manager.list_derived_metrics()
        return base_metrics + derived_metrics

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        uptime = time.time() - self._stats["start_time"]
        metrics_per_second = (
            self._stats["total_metrics_recorded"] / uptime if uptime > 0 else 0
        )

        return {
            "uptime_seconds": uptime,
            "total_metrics": len(self.metric_definitions),
            "total_derived_metrics": len(
                self.derived_metrics_manager.list_derived_metrics()
            ),
            "total_metrics_recorded": self._stats["total_metrics_recorded"],
            "total_computations": self._stats["total_computations"],
            "errors": self._stats["errors"],
            "metrics_per_second": metrics_per_second,
            "derived_metrics": {
                "total_derived_metrics": len(
                    self.derived_metrics_manager.list_derived_metrics()
                ),
                "active_metrics": len(
                    [
                        m
                        for m in self.derived_metrics_manager.list_derived_metrics()
                        if await self.get_metric_value(m) is not None
                    ]
                ),
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "metrics_count": len(self.metric_definitions),
            "derived_metrics_count": len(
                self.derived_metrics_manager.list_derived_metrics()
            ),
        }

    async def cleanup_expired_metrics(self) -> BatchResult:
        """Clean up expired metrics."""
        start_time = time.time()
        result = BatchResult(total_processed=0, successful=0, failed=0)

        for metric_id, raw_store in self.raw_stores.items():
            result.total_processed += 1
            try:
                cleaned = await raw_store.cleanup_expired(metric_id)
                if cleaned > 0:
                    result.successful += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"{metric_id}: {str(e)}")

        result.processing_time_seconds = time.time() - start_time
        await self.metrics.record_cleanup(
            result.processing_time_seconds, result.successful
        )
        return result

    async def export_metrics(
        self, metric_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Export metrics data."""
        if metric_ids is None:
            metric_ids = await self.list_metrics()

        exported = {}
        for metric_id in metric_ids:
            value = await self.get_metric_value(metric_id)
            if value:
                exported[metric_id] = value.model_dump()

        return {"metrics": exported, "timestamp": time.time()}

    def _start_background_cleanup(self) -> None:
        """Start background cleanup task."""

        async def cleanup_loop() -> None:
            while not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(self.config.cleanup_interval_seconds)
                    if not self._shutdown_event.is_set():
                        await self.cleanup_expired_metrics()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in background cleanup: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def shutdown(self) -> None:
        """Shutdown the metric store."""
        self.logger.info("Shutting down metric store...")
        self._shutdown_event.set()

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Metric store shutdown complete")
