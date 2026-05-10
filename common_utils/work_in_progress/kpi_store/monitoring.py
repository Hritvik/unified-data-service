"""
Monitoring and self-metrics for the KPI store system.

This module provides monitoring capabilities and self-metrics collection
for the KPI store system itself.
"""

import time
from typing import Any, Dict, List, Optional

from common_utils.logger import get_logger
from common_utils.metrics import track_metric_async

logger = get_logger(__name__)


class KPIStoreMetrics:
    """Self-monitoring metrics for the KPI store system."""

    def __init__(self, prefix: str = "kpi_store.") -> None:
        self.prefix = prefix
        self.logger = logger

        # Internal counters
        self._counters = {
            "operations_total": 0,
            "operations_successful": 0,
            "operations_failed": 0,
            "samples_recorded": 0,
            "computations_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cleanup_operations": 0,
        }

        # Timing data
        self._timing_data = {
            "operation_durations": [],
            "computation_durations": [],
            "cleanup_durations": [],
        }

        # System metrics
        self._system_metrics = {
            "memory_usage_bytes": 0,
            "active_metrics": 0,
            "derived_metrics": 0,
            "error_rate": 0.0,
        }

    async def record_operation(
        self, operation: str, success: bool = True, duration: Optional[float] = None
    ) -> None:
        """Record a metric store operation."""
        try:
            self._counters["operations_total"] += 1

            if success:
                self._counters["operations_successful"] += 1
            else:
                self._counters["operations_failed"] += 1

            if duration is not None:
                self._timing_data["operation_durations"].append(duration)
                # Keep only recent durations (last 1000)
                if len(self._timing_data["operation_durations"]) > 1000:
                    self._timing_data["operation_durations"] = self._timing_data[
                        "operation_durations"
                    ][-1000:]

            # Track in unified metrics system
            await track_metric_async(
                "kpi_store",
                "counter",
                f"{self.prefix}operations_total",
                labels={
                    "operation": operation,
                    "status": "success" if success else "error",
                },
            )

            if duration is not None:
                await track_metric_async(
                    "kpi_store",
                    "histogram",
                    f"{self.prefix}operation_duration_seconds",
                    value=duration,
                    labels={"operation": operation},
                )

        except Exception as e:
            self.logger.error(f"Error recording operation metric: {e}")

    async def record_sample(self, metric_id: str, count: int = 1) -> None:
        """Record samples being added."""
        try:
            self._counters["samples_recorded"] += count

            await track_metric_async(
                "kpi_store",
                "counter",
                f"{self.prefix}samples_recorded_total",
                value=count,
                labels={"metric_id": metric_id},
            )

        except Exception as e:
            self.logger.error(f"Error recording sample metric: {e}")

    async def record_computation(
        self, metric_id: str, algorithm: str, duration: float, success: bool = True
    ) -> None:
        """Record a metric computation."""
        try:
            self._counters["computations_total"] += 1
            self._timing_data["computation_durations"].append(duration)

            # Keep only recent durations
            if len(self._timing_data["computation_durations"]) > 1000:
                self._timing_data["computation_durations"] = self._timing_data[
                    "computation_durations"
                ][-1000:]

            await track_metric_async(
                "kpi_store",
                "counter",
                f"{self.prefix}computations_total",
                labels={
                    "metric_id": metric_id,
                    "algorithm": algorithm,
                    "status": "success" if success else "error",
                },
            )

            await track_metric_async(
                "kpi_store",
                "histogram",
                f"{self.prefix}computation_duration_seconds",
                value=duration,
                labels={"algorithm": algorithm},
            )

        except Exception as e:
            self.logger.error(f"Error recording computation metric: {e}")

    async def record_cache_operation(self, hit: bool) -> None:
        """Record cache hit/miss."""
        try:
            if hit:
                self._counters["cache_hits"] += 1
            else:
                self._counters["cache_misses"] += 1

            await track_metric_async(
                "kpi_store",
                "counter",
                f"{self.prefix}cache_operations_total",
                labels={"result": "hit" if hit else "miss"},
            )

        except Exception as e:
            self.logger.error(f"Error recording cache metric: {e}")

    async def record_cleanup(self, duration: float, items_cleaned: int) -> None:
        """Record cleanup operation."""
        try:
            self._counters["cleanup_operations"] += 1
            self._timing_data["cleanup_durations"].append(duration)

            await track_metric_async(
                "kpi_store", "counter", f"{self.prefix}cleanup_operations_total"
            )

            await track_metric_async(
                "kpi_store",
                "histogram",
                f"{self.prefix}cleanup_duration_seconds",
                value=duration,
            )

            await track_metric_async(
                "kpi_store",
                "gauge",
                f"{self.prefix}cleanup_items_processed",
                value=items_cleaned,
            )

        except Exception as e:
            self.logger.error(f"Error recording cleanup metric: {e}")

    async def update_system_metrics(
        self,
        memory_usage: int,
        active_metrics: int,
        derived_metrics: int,
        error_rate: float,
    ) -> None:
        """Update system-level metrics."""
        try:
            self._system_metrics.update(
                {
                    "memory_usage_bytes": memory_usage,
                    "active_metrics": active_metrics,
                    "derived_metrics": derived_metrics,
                    "error_rate": error_rate,
                }
            )

            await track_metric_async(
                "kpi_store",
                "gauge",
                f"{self.prefix}memory_usage_bytes",
                value=memory_usage,
            )

            await track_metric_async(
                "kpi_store",
                "gauge",
                f"{self.prefix}active_metrics_count",
                value=active_metrics,
            )

            await track_metric_async(
                "kpi_store",
                "gauge",
                f"{self.prefix}derived_metrics_count",
                value=derived_metrics,
            )

            await track_metric_async(
                "kpi_store", "gauge", f"{self.prefix}error_rate", value=error_rate
            )

        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")

    def get_counters(self) -> Dict[str, int]:
        """Get current counter values."""
        return self._counters.copy()

    def get_timing_stats(self) -> Dict[str, Dict[str, float]]:
        """Get timing statistics."""
        stats = {}

        for key, durations in self._timing_data.items():
            if durations:
                stats[key] = {
                    "count": len(durations),
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "p95": self._percentile(durations, 95),
                    "p99": self._percentile(durations, 99),
                }
            else:
                stats[key] = {
                    "count": 0,
                    "avg": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }

        return stats

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        return self._system_metrics.copy()

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of numbers."""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_data) - 1)

        if lower_index == upper_index:
            return sorted_data[lower_index]

        weight = index - lower_index
        return (
            sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
        )

    def reset_counters(self) -> None:
        """Reset all counters (useful for testing)."""
        for key in self._counters:
            self._counters[key] = 0

        for key in self._timing_data:
            self._timing_data[key] = []


class KPIStoreHealthChecker:
    """Health checker for the KPI store system."""

    def __init__(self, kpi_store: Any) -> None:
        self.kpi_store = kpi_store
        self.logger = logger

        # Health thresholds
        self.thresholds = {
            "max_error_rate": 0.1,  # 10%
            "max_avg_operation_time": 1.0,  # 1 second
            "max_memory_usage_mb": 1000,  # 1GB
            "min_success_rate": 0.95,  # 95%
        }

    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_report = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {},
            "metrics": {},
            "recommendations": [],
        }

        try:
            # Check basic connectivity
            health_report["checks"]["connectivity"] = await self._check_connectivity()

            # Check performance metrics
            health_report["checks"]["performance"] = await self._check_performance()

            # Check resource usage
            health_report["checks"]["resources"] = await self._check_resources()

            # Check error rates
            health_report["checks"]["error_rates"] = await self._check_error_rates()

            # Check storage backends
            health_report["checks"]["storage"] = await self._check_storage_backends()

            # Determine overall health
            failed_checks = [
                check_name
                for check_name, result in health_report["checks"].items()
                if not result.get("healthy", True)
            ]

            if failed_checks:
                health_report["status"] = (
                    "unhealthy" if len(failed_checks) > 2 else "degraded"
                )
                health_report["failed_checks"] = failed_checks

            # Get current metrics
            health_report["metrics"] = await self._get_health_metrics()

            # Generate recommendations
            health_report["recommendations"] = await self._generate_recommendations(
                health_report
            )

        except Exception as e:
            self.logger.error(f"Error during health check: {e}")
            health_report["status"] = "unhealthy"
            health_report["error"] = str(e)

        return health_report

    async def _check_connectivity(self) -> Dict[str, Any]:
        """Check basic connectivity to storage backends."""
        result = {"healthy": True, "details": {}}

        try:
            # Check Redis connectivity if using Redis
            if hasattr(self.kpi_store, "redis_client") and self.kpi_store.redis_client:
                redis_health = await self.kpi_store.redis_client.ping()
                result["details"]["redis"] = {
                    "healthy": redis_health,
                    "status": "connected" if redis_health else "disconnected",
                }

                if not redis_health:
                    result["healthy"] = False

            # Check metric store basic operations
            test_metrics = await self.kpi_store.list_metrics()
            result["details"]["kpi_store"] = {
                "healthy": True,
                "total_metrics": len(test_metrics),
            }

        except Exception as e:
            result["healthy"] = False
            result["error"] = str(e)

        return result

    async def _check_performance(self) -> Dict[str, Any]:
        """Check performance metrics."""
        result = {"healthy": True, "details": {}}

        try:
            # Get timing statistics from metrics
            if hasattr(self.kpi_store, "_stats"):
                stats = self.kpi_store._stats

                # Check operation performance
                uptime = time.time() - stats.get("start_time", time.time())
                if uptime > 0:
                    ops_per_second = stats.get("total_metrics_recorded", 0) / uptime
                    result["details"]["operations_per_second"] = ops_per_second

                    # Check if performance is acceptable
                    if (
                        ops_per_second < 1
                        and stats.get("total_metrics_recorded", 0) > 100
                    ):
                        result["healthy"] = False
                        result["details"][
                            "performance_issue"
                        ] = "Low throughput detected"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _check_resources(self) -> Dict[str, Any]:
        """Check resource usage."""
        result = {"healthy": True, "details": {}}

        try:
            # Estimate memory usage
            total_metrics = len(await self.kpi_store.list_metrics())
            estimated_memory_mb = total_metrics * 0.1  # Rough estimate

            result["details"]["estimated_memory_mb"] = estimated_memory_mb
            result["details"]["total_metrics"] = total_metrics

            # Check against thresholds
            if estimated_memory_mb > self.thresholds["max_memory_usage_mb"]:
                result["healthy"] = False
                result["details"]["memory_warning"] = "High memory usage detected"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _check_error_rates(self) -> Dict[str, Any]:
        """Check error rates."""
        result = {"healthy": True, "details": {}}

        try:
            if hasattr(self.kpi_store, "_stats"):
                stats = self.kpi_store._stats

                total_ops = stats.get("total_metrics_recorded", 0) + stats.get(
                    "total_computations", 0
                )
                errors = stats.get("errors", 0)

                if total_ops > 0:
                    error_rate = errors / total_ops
                    result["details"]["error_rate"] = error_rate
                    result["details"]["total_operations"] = total_ops
                    result["details"]["total_errors"] = errors

                    if error_rate > self.thresholds["max_error_rate"]:
                        result["healthy"] = False
                        result["details"][
                            "error_warning"
                        ] = f"High error rate: {error_rate:.2%}"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _check_storage_backends(self) -> Dict[str, Any]:
        """Check storage backend health."""
        result = {"healthy": True, "details": {}}

        try:
            # Check raw stores
            raw_stores_healthy = 0
            total_raw_stores = len(getattr(self.kpi_store, "raw_stores", {}))

            for metric_id, raw_store in getattr(
                self.kpi_store, "raw_stores", {}
            ).items():
                try:
                    # Try a basic operation
                    await raw_store.get_sample_count(metric_id)
                    raw_stores_healthy += 1
                except Exception:
                    pass

            result["details"]["raw_stores"] = {
                "healthy": raw_stores_healthy,
                "total": total_raw_stores,
                "health_rate": raw_stores_healthy / total_raw_stores
                if total_raw_stores > 0
                else 1.0,
            }

            # Check final stores
            final_stores_healthy = 0
            total_final_stores = len(getattr(self.kpi_store, "final_stores", {}))

            for metric_id, final_store in getattr(
                self.kpi_store, "final_stores", {}
            ).items():
                try:
                    # Try a basic operation
                    await final_store.get_metric_value(metric_id)
                    final_stores_healthy += 1
                except Exception:
                    pass

            result["details"]["final_stores"] = {
                "healthy": final_stores_healthy,
                "total": total_final_stores,
                "health_rate": final_stores_healthy / total_final_stores
                if total_final_stores > 0
                else 1.0,
            }

            # Overall storage health
            total_stores = total_raw_stores + total_final_stores
            healthy_stores = raw_stores_healthy + final_stores_healthy

            if total_stores > 0 and (healthy_stores / total_stores) < 0.8:
                result["healthy"] = False
                result["details"][
                    "storage_warning"
                ] = "Multiple storage backends unhealthy"

        except Exception as e:
            result["error"] = str(e)

        return result

    async def _get_health_metrics(self) -> Dict[str, Any]:
        """Get current health-related metrics."""
        try:
            return await self.kpi_store.get_system_stats()
        except Exception as e:
            self.logger.error(f"Error getting health metrics: {e}")
            return {}

    async def _generate_recommendations(
        self, health_report: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on health check results."""
        recommendations = []

        try:
            # Check for performance issues
            if not health_report["checks"].get("performance", {}).get("healthy", True):
                recommendations.append(
                    "Consider optimizing metric computation algorithms or increasing resources"
                )

            # Check for memory issues
            resources_check = health_report["checks"].get("resources", {})
            if not resources_check.get("healthy", True):
                recommendations.append(
                    "Consider implementing more aggressive cleanup policies or increasing memory limits"
                )

            # Check for error rate issues
            error_check = health_report["checks"].get("error_rates", {})
            if not error_check.get("healthy", True):
                recommendations.append(
                    "Investigate error patterns and consider implementing circuit breakers"
                )

            # Check for storage issues
            storage_check = health_report["checks"].get("storage", {})
            if not storage_check.get("healthy", True):
                recommendations.append(
                    "Check storage backend connectivity and consider implementing fallback mechanisms"
                )

            # General recommendations
            total_metrics = (
                health_report.get("metrics", {})
                .get("derived_metrics", {})
                .get("total_derived_metrics", 0)
            )
            if total_metrics > 100:
                recommendations.append(
                    "Consider partitioning metrics across multiple instances for better scalability"
                )

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")

        return recommendations


# Global instances for easy access
metric_store_metrics = KPIStoreMetrics()


async def get_metric_store_health_checker(
    metric_store: Any,
) -> KPIStoreHealthChecker:
    """Get a health checker instance for a metric store."""
    return KPIStoreHealthChecker(metric_store)
