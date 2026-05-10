"""
TTL-based load-on-miss cache mixin.

Provides a mixin for single-value, TTL-based in-memory caching with async
_load_data and load_data_with_cache. Distinct from ICacheRepository
(key-value store). Use for services that load one blob (e.g. config, registry
snapshot) and want TTL + refresh_cache for lifecycle/registry integration.
"""

from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar

from common_utils.timezone_utils import get_utc_now

T = TypeVar("T")


class CacheMixin(Generic[T]):
    """
    Mixin for TTL-based single-value caching with async load-on-miss.

    Use with classes that need to cache one value (e.g. config, registry data)
    with a configurable TTL. Implement _load_data(); call load_data_with_cache().
    refresh_cache() clears the cache for lifecycle/registry integration.
    """

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        self._cache: Optional[T] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl: int = default_ttl_seconds

    def _clear_cache(self) -> None:
        """Clear the cache and reset timestamp."""
        self._cache = None
        self._cache_timestamp = None

    def _is_cache_valid(self) -> bool:
        if not self._cache_timestamp or self._cache is None:
            return False
        time_diff = (get_utc_now() - self._cache_timestamp).total_seconds()
        return time_diff < self._cache_ttl

    def _update_cache(self, data: T) -> None:
        self._cache = data
        self._cache_timestamp = get_utc_now()

    def _get_cached_data(self) -> Optional[T]:
        if self._is_cache_valid():
            return self._cache
        return None

    def set_cache_ttl(self, ttl_seconds: int) -> None:
        self._cache_ttl = ttl_seconds

    def get_cache_ttl(self) -> int:
        return self._cache_ttl

    def refresh_cache(self) -> None:
        """Force a cache refresh by clearing the cache."""
        self._clear_cache()

    def get_cache_info(self) -> Dict[str, Any]:
        cache_age: Optional[float] = None
        if self._cache_timestamp:
            cache_age = (get_utc_now() - self._cache_timestamp).total_seconds()
        return {
            "cache_ttl": self._cache_ttl,
            "cache_age_seconds": cache_age,
            "cache_timestamp": self._cache_timestamp,
            "is_cache_valid": self._is_cache_valid(),
            "has_cached_data": self._cache is not None,
        }

    async def _load_data(self) -> T:
        """Override in subclasses to define how data is loaded from the source."""
        raise NotImplementedError("Subclasses must implement _load_data method")

    async def load_data_with_cache(self) -> T:
        """Return valid cached data, or load via _load_data, cache, and return."""
        from common_utils.cache.metrics import track_mixin_hit, track_mixin_miss

        cached_data = self._get_cached_data()
        if cached_data is not None:
            try:
                await track_mixin_hit(self.__class__.__name__)
            except Exception:
                pass
            return cached_data
        try:
            await track_mixin_miss(self.__class__.__name__)
        except Exception:
            pass
        fresh_data = await self._load_data()
        self._update_cache(fresh_data)
        return fresh_data
