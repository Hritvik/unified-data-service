"""
Cache metrics for common_utils.cache (repository hit/miss/set/delete/errors, mixin hit/miss).

Uses the common_utils metrics infrastructure. Metrics are auto-registered on first use.
"""


from common_utils.metrics import register_module_metrics, track_metric_async

CACHE_METRICS_DEFINITIONS = {
    "repository_hits_total": {
        "type": "counter",
        "description": "Cache repository get hits",
        "labels": ["cache_name", "backend"],
    },
    "repository_misses_total": {
        "type": "counter",
        "description": "Cache repository get misses",
        "labels": ["cache_name", "backend"],
    },
    "repository_sets_total": {
        "type": "counter",
        "description": "Cache repository set operations",
        "labels": ["cache_name", "backend"],
    },
    "repository_deletes_total": {
        "type": "counter",
        "description": "Cache repository delete operations",
        "labels": ["cache_name", "backend"],
    },
    "repository_errors_total": {
        "type": "counter",
        "description": "Cache repository operation errors",
        "labels": ["cache_name", "backend", "operation"],
    },
    "mixin_hits_total": {
        "type": "counter",
        "description": "CacheMixin load_data_with_cache hits",
        "labels": ["cache"],
    },
    "mixin_misses_total": {
        "type": "counter",
        "description": "CacheMixin load_data_with_cache misses",
        "labels": ["cache"],
    },
}


def register_cache_metrics() -> None:
    """Register cache module metrics."""
    register_module_metrics("cache", CACHE_METRICS_DEFINITIONS)


async def track_repository_hit(cache_name: str, backend: str, count: int = 1) -> None:
    await track_metric_async(
        "cache",
        "counter",
        "repository_hits_total",
        count,
        {"cache_name": cache_name, "backend": backend},
    )


async def track_repository_miss(cache_name: str, backend: str, count: int = 1) -> None:
    await track_metric_async(
        "cache",
        "counter",
        "repository_misses_total",
        count,
        {"cache_name": cache_name, "backend": backend},
    )


async def track_repository_set(cache_name: str, backend: str, count: int = 1) -> None:
    await track_metric_async(
        "cache",
        "counter",
        "repository_sets_total",
        count,
        {"cache_name": cache_name, "backend": backend},
    )


async def track_repository_delete(
    cache_name: str, backend: str, count: int = 1
) -> None:
    await track_metric_async(
        "cache",
        "counter",
        "repository_deletes_total",
        count,
        {"cache_name": cache_name, "backend": backend},
    )


async def track_repository_error(cache_name: str, backend: str, operation: str) -> None:
    await track_metric_async(
        "cache",
        "counter",
        "repository_errors_total",
        1,
        {"cache_name": cache_name, "backend": backend, "operation": operation},
    )


async def track_mixin_hit(cache: str) -> None:
    await track_metric_async(
        "cache", "counter", "mixin_hits_total", 1, {"cache": cache}
    )


async def track_mixin_miss(cache: str) -> None:
    await track_metric_async(
        "cache", "counter", "mixin_misses_total", 1, {"cache": cache}
    )


__all__ = [
    "register_cache_metrics",
    "track_repository_hit",
    "track_repository_miss",
    "track_repository_set",
    "track_repository_delete",
    "track_repository_error",
    "track_mixin_hit",
    "track_mixin_miss",
]
