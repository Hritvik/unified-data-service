"""
Standard way to track DI container instance creation.

This module provides utilities for tracking singleton instance creation
in dependency-injector containers without breaking provider functionality.
"""

from typing import Any, Callable, TypeVar

from dependency_injector import providers

# Track singleton instance IDs to detect leaks
_singleton_instance_ids: dict[str, set[int]] = {}

T = TypeVar("T")


def tracked_singleton(
    factory: Callable[..., T],
    container_name: str,
    provider_name: str,
    **kwargs: Any,
) -> providers.Singleton:
    """
    Create a Singleton provider that tracks instance creation.

    This is the standard way to track instances in dependency-injector:
    - Returns an actual Provider instance (works with override())
    - Tracks metrics when instances are created
    - Doesn't break any DI container functionality

    Args:
        factory: The class or callable to instantiate
        container_name: Name of the container (for metrics)
        provider_name: Name of the provider (for metrics)
        **kwargs: Keyword arguments to pass to factory (e.g., dependencies)

    Returns:
        A Singleton provider that tracks instance creation

    Example:
        ```python
        # Simple case
        cache_registry = tracked_singleton(CacheRegistry, "app", "cache_registry")

        # With dependencies
        cache_handler = tracked_singleton(
            CacheHandler, "app", "cache_handler", cache_registry=cache_registry
        )
        ```
    """

    # Create a factory function that wraps the original factory
    def tracked_factory(**factory_kwargs: Any) -> T:
        # Track provider access
        try:
            from common_utils.metrics import track_metric_sync

            track_metric_sync(
                "app",
                "counter",
                "di_container_provider_access_total",
                1.0,
                {"container": container_name, "provider": provider_name},
            )
        except Exception:
            pass

        # Create the instance (factory_kwargs already contains resolved dependencies)
        instance = factory(**factory_kwargs)

        # Track instance creation
        try:
            from common_utils.metrics import track_metric_sync

            instance_id = id(instance)
            key = f"{container_name}.{provider_name}"
            if key not in _singleton_instance_ids:
                _singleton_instance_ids[key] = set()
            _singleton_instance_ids[key].add(instance_id)

            unique_count = len(_singleton_instance_ids[key])
            track_metric_sync(
                "app",
                "gauge",
                "di_container_singleton_instances",
                unique_count,
                {"container": container_name, "provider": provider_name},
            )
        except Exception:
            pass

        return instance

    # Return a standard Singleton provider with kwargs (dependency-injector will resolve providers)
    return providers.Singleton(tracked_factory, **kwargs)
