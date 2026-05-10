"""In-memory cache repository with TTL, bulk, pattern, and stats."""

import asyncio
import fnmatch
import sys
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from common_utils.logger import get_logger

from .interfaces import CacheStats, ICacheRepository
from .metrics import (
    track_repository_delete,
    track_repository_hit,
    track_repository_miss,
    track_repository_set,
)

T = TypeVar("T")
logger = get_logger(__name__)

_BACKEND_MEMORY = "memory"


class InMemoryCacheRepository(ICacheRepository[T]):
    """
    In-memory implementation with TTL, bulk, pattern, and statistics.

    Suitable for development, testing, and when Redis is not available.
    """

    def __init__(
        self,
        key_extractor: Callable[[T], str],
        default_ttl_seconds: Optional[int] = None,
        cache_name: Optional[str] = None,
    ) -> None:
        self._key_extractor = key_extractor
        self._default_ttl = default_ttl_seconds
        self._cache_name = cache_name or "default"
        self._storage: Dict[str, T] = {}
        self._ttl_storage: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        self.logger = logger

    def _get_entity_key(self, entity: T) -> str:
        return self._key_extractor(entity)

    def _do_cleanup_expired(self) -> int:
        """Remove expired entries. Must be called with _lock held."""
        current_time = time.time()
        expired = [k for k, t in self._ttl_storage.items() if current_time > t]
        for k in expired:
            self._storage.pop(k, None)
            self._ttl_storage.pop(k, None)
        if expired:
            self.logger.debug(f"Cleaned up {len(expired)} expired entries")
        return len(expired)

    # --- Single-key ---
    async def get_by_key(self, key: str) -> Optional[T]:
        async with self._lock:
            if key in self._ttl_storage and time.time() > self._ttl_storage[key]:
                self._storage.pop(key, None)
                self._ttl_storage.pop(key, None)
                self._stats.misses += 1
                val: Optional[T] = None
            else:
                val = self._storage.get(key)
                if val is not None:
                    self._stats.hits += 1
                else:
                    self._stats.misses += 1
        try:
            if val is not None:
                await track_repository_hit(self._cache_name, _BACKEND_MEMORY)
            else:
                await track_repository_miss(self._cache_name, _BACKEND_MEMORY)
        except Exception:
            pass
        return val

    async def set_by_key(
        self, key: str, entity: T, ttl_seconds: Optional[int] = None
    ) -> T:
        async with self._lock:
            self._storage[key] = entity
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            if ttl is not None:
                self._ttl_storage[key] = time.time() + ttl
            else:
                self._ttl_storage.pop(key, None)
            self._stats.sets += 1
            self._stats.total_keys = len(self._storage)
            self.logger.debug(f"Stored entity with key: {key} (TTL: {ttl}s)")
        try:
            await track_repository_set(self._cache_name, _BACKEND_MEMORY)
        except Exception:
            pass
        return entity

    async def set_with_ttl(self, key: str, entity: T, ttl_seconds: int) -> T:
        return await self.set_by_key(key, entity, ttl_seconds)

    async def delete_by_key(self, key: str) -> bool:
        deleted = False
        async with self._lock:
            if key in self._storage:
                del self._storage[key]
                self._ttl_storage.pop(key, None)
                self._stats.deletes += 1
                self._stats.total_keys = len(self._storage)
                self.logger.debug(f"Deleted entity with key: {key}")
                deleted = True
        if deleted:
            try:
                await track_repository_delete(self._cache_name, _BACKEND_MEMORY)
            except Exception:
                pass
        return deleted

    async def exists_by_key(self, key: str) -> bool:
        async with self._lock:
            if key in self._ttl_storage and time.time() > self._ttl_storage[key]:
                self._storage.pop(key, None)
                self._ttl_storage.pop(key, None)
                return False
            return key in self._storage

    async def get_all(self) -> Dict[str, T]:
        async with self._lock:
            self._do_cleanup_expired()
            return self._storage.copy()

    async def get_all_keys(self) -> List[str]:
        async with self._lock:
            self._do_cleanup_expired()
            return list(self._storage.keys())

    async def count(self) -> int:
        async with self._lock:
            self._do_cleanup_expired()
            return len(self._storage)

    async def clear(self) -> None:
        async with self._lock:
            n = len(self._storage)
            self._storage.clear()
            self._ttl_storage.clear()
            self.logger.info(f"Cleared {n} entities from cache")

    async def cleanup_expired(self) -> int:
        async with self._lock:
            return self._do_cleanup_expired()

    def get_cache_info(self) -> Dict[str, Any]:
        return {
            "backend": "in-memory",
            "total_entries": len(self._storage),
            "ttl_entries": len(self._ttl_storage),
            "default_ttl": self._default_ttl,
            "keys": list(self._storage.keys()),
            "supports_bulk_operations": True,
            "supports_pattern_operations": True,
            "statistics_enabled": True,
        }

    # --- Bulk ---
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[T]]:
        async with self._lock:
            result: Dict[str, Optional[T]] = {}
            now = time.time()
            for key in keys:
                if key in self._ttl_storage and now > self._ttl_storage[key]:
                    self._storage.pop(key, None)
                    self._ttl_storage.pop(key, None)
                    result[key] = None
                    self._stats.misses += 1
                else:
                    v = self._storage.get(key)
                    result[key] = v
                    if v is not None:
                        self._stats.hits += 1
                    else:
                        self._stats.misses += 1
            self._stats.bulk_operations += 1
            self.logger.debug(f"Bulk get for {len(keys)} keys")
        try:
            hits = sum(1 for v in result.values() if v is not None)
            misses = len(keys) - hits
            if hits:
                await track_repository_hit(self._cache_name, _BACKEND_MEMORY, hits)
            if misses:
                await track_repository_miss(self._cache_name, _BACKEND_MEMORY, misses)
        except Exception:
            pass
        return result

    async def set_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> None:
        async with self._lock:
            now = time.time()
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            for key, entity in items.items():
                self._storage[key] = entity
                if ttl is not None:
                    self._ttl_storage[key] = now + ttl
                else:
                    self._ttl_storage.pop(key, None)
            self._stats.sets += len(items)
            self._stats.bulk_operations += 1
            self._stats.total_keys = len(self._storage)
            self.logger.debug(f"Bulk set for {len(items)} items (TTL: {ttl}s)")
        try:
            if items:
                await track_repository_set(
                    self._cache_name, _BACKEND_MEMORY, len(items)
                )
        except Exception:
            pass

    async def delete_many(self, keys: List[str]) -> int:
        n = 0
        async with self._lock:
            for key in keys:
                if key in self._storage:
                    del self._storage[key]
                    self._ttl_storage.pop(key, None)
                    n += 1
            self._stats.deletes += n
            self._stats.bulk_operations += 1
            self._stats.total_keys = len(self._storage)
            self.logger.debug(f"Bulk delete: {n}/{len(keys)} keys")
        if n:
            try:
                await track_repository_delete(self._cache_name, _BACKEND_MEMORY, n)
            except Exception:
                pass
        return n

    # --- Pattern ---
    async def get_by_pattern(self, pattern: str) -> Dict[str, T]:
        async with self._lock:
            result: Dict[str, T] = {}
            now = time.time()
            for key in list(self._storage.keys()):
                if not fnmatch.fnmatch(key, pattern):
                    continue
                if key in self._ttl_storage and now > self._ttl_storage[key]:
                    self._storage.pop(key, None)
                    self._ttl_storage.pop(key, None)
                    self._stats.misses += 1
                    continue
                result[key] = self._storage[key]
                self._stats.hits += 1
            self.logger.debug(f"Pattern get '{pattern}': {len(result)} items")
            return result

    async def delete_by_pattern(self, pattern: str) -> int:
        async with self._lock:
            to_del = [k for k in self._storage if fnmatch.fnmatch(k, pattern)]
            for k in to_del:
                del self._storage[k]
                self._ttl_storage.pop(k, None)
            self._stats.deletes += len(to_del)
            self._stats.total_keys = len(self._storage)
            self.logger.debug(f"Pattern delete '{pattern}': {len(to_del)} items")
            return len(to_del)

    async def count_by_pattern(self, pattern: str) -> int:
        async with self._lock:
            self._do_cleanup_expired()
            return sum(1 for k in self._storage if fnmatch.fnmatch(k, pattern))

    # --- Warming ---
    async def warm_cache(self, data_loader: Callable[[], Dict[str, T]]) -> int:
        try:
            data = data_loader()
            await self.set_many(data, self._default_ttl)
            self.logger.info(f"Cache warmed with {len(data)} items")
            return len(data)
        except Exception as e:
            self.logger.error(f"Error warming cache: {e}")
            return 0

    async def preload_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> int:
        await self.set_many(items, ttl_seconds)
        self.logger.info(f"Preloaded {len(items)} items into cache")
        return len(items)

    # --- Stats ---
    async def get_cache_stats(self) -> Dict[str, Any]:
        async with self._lock:
            self._stats.total_keys = len(self._storage)
            return self._stats.to_dict()

    async def get_memory_usage(self) -> Dict[str, Any]:
        async with self._lock:
            so = sys.getsizeof(self._storage) + sys.getsizeof(self._ttl_storage)
            es = sum(sys.getsizeof(v) for v in self._storage.values())
            ks = sum(sys.getsizeof(k) for k in self._storage.keys())
            n = max(len(self._storage), 1)
            return {
                "total_memory_bytes": so + es + ks,
                "storage_overhead_bytes": so,
                "entity_data_bytes": es,
                "key_data_bytes": ks,
                "total_keys": len(self._storage),
                "average_entity_size_bytes": es // n,
                "average_key_size_bytes": ks // n,
            }
