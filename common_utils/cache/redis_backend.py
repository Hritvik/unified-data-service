"""Redis cache repository with TTL, bulk, pattern, and stats."""

from typing import Any, Callable, Dict, List, Optional, TypeVar

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from .interfaces import CacheStats, ICacheRepository
from .memory import InMemoryCacheRepository
from .metrics import (
    track_repository_delete,
    track_repository_error,
    track_repository_hit,
    track_repository_miss,
    track_repository_set,
)

T = TypeVar("T")
logger = get_logger(__name__)

_BACKEND_REDIS = "redis"


class RedisCacheRepository(ICacheRepository[T]):
    """
    Redis implementation with TTL, bulk, pattern, and statistics.

    Falls back to InMemoryCacheRepository when redis_client is not provided.
    """

    def __init__(
        self,
        key_extractor: Callable[[T], str],
        redis_client: Optional[RedisClient] = None,
        default_ttl_seconds: Optional[int] = None,
        cache_name: Optional[str] = None,
    ) -> None:
        self._key_extractor = key_extractor
        self._redis_client = redis_client
        self._default_ttl = default_ttl_seconds
        self._cache_name = cache_name or "default"
        self._stats = CacheStats()
        self.logger = logger
        self._fallback_repo: Optional[InMemoryCacheRepository[T]] = None
        if not self._redis_client:
            self.logger.warning(
                "Redis client not provided, falling back to in-memory storage"
            )
            self._fallback_repo = InMemoryCacheRepository[T](
                key_extractor=key_extractor,
                default_ttl_seconds=default_ttl_seconds,
                cache_name=self._cache_name,
            )

    # --- Single-key ---
    async def get_by_key(self, key: str) -> Optional[T]:
        if self._fallback_repo:
            return await self._fallback_repo.get_by_key(key)
        try:
            v = await self._redis_client.get(key)
            if v is not None:
                self._stats.hits += 1
                await track_repository_hit(self._cache_name, _BACKEND_REDIS)
            else:
                self._stats.misses += 1
                await track_repository_miss(self._cache_name, _BACKEND_REDIS)
            return v
        except Exception as e:
            self.logger.error(f"Error getting key {key}: {e}")
            self._stats.misses += 1
            await track_repository_error(self._cache_name, _BACKEND_REDIS, "get")
            return None

    async def set_by_key(
        self, key: str, entity: T, ttl_seconds: Optional[int] = None
    ) -> T:
        if self._fallback_repo:
            return await self._fallback_repo.set_by_key(key, entity, ttl_seconds)
        try:
            ttl = ttl_seconds or self._default_ttl
            await self._redis_client.set(key, entity, ttl)
            self._stats.sets += 1
            await track_repository_set(self._cache_name, _BACKEND_REDIS)
            return entity
        except Exception as e:
            self.logger.error(f"Error setting key {key}: {e}")
            await track_repository_error(self._cache_name, _BACKEND_REDIS, "set")
            return entity

    async def set_with_ttl(self, key: str, entity: T, ttl_seconds: int) -> T:
        return await self.set_by_key(key, entity, ttl_seconds)

    async def delete_by_key(self, key: str) -> bool:
        if self._fallback_repo:
            return await self._fallback_repo.delete_by_key(key)
        try:
            ok = await self._redis_client.delete(key)
            if ok:
                self._stats.deletes += 1
                await track_repository_delete(self._cache_name, _BACKEND_REDIS)
            return ok
        except Exception as e:
            self.logger.error(f"Error deleting key {key}: {e}")
            await track_repository_error(self._cache_name, _BACKEND_REDIS, "delete")
            return False

    async def exists_by_key(self, key: str) -> bool:
        if self._fallback_repo:
            return await self._fallback_repo.exists_by_key(key)
        try:
            return await self._redis_client.exists(key)
        except Exception as e:
            self.logger.error(f"Error checking existence of key {key}: {e}")
            return False

    async def get_all(self) -> Dict[str, T]:
        if self._fallback_repo:
            return await self._fallback_repo.get_all()
        try:
            return await self._redis_client.get_all()
        except Exception as e:
            self.logger.error(f"Error getting all entities: {e}")
            return {}

    async def get_all_keys(self) -> List[str]:
        if self._fallback_repo:
            return await self._fallback_repo.get_all_keys()
        try:
            return await self._redis_client.keys()
        except Exception as e:
            self.logger.error(f"Error getting all keys: {e}")
            return []

    async def count(self) -> int:
        if self._fallback_repo:
            return await self._fallback_repo.count()
        try:
            return await self._redis_client.count()
        except Exception as e:
            self.logger.error(f"Error counting entities: {e}")
            return 0

    async def clear(self) -> None:
        if self._fallback_repo:
            await self._fallback_repo.clear()
            return
        try:
            await self._redis_client.clear()
        except Exception as e:
            self.logger.error(f"Error clearing entities: {e}")

    async def cleanup_expired(self) -> int:
        if self._fallback_repo:
            return await self._fallback_repo.cleanup_expired()
        self.logger.debug("Redis handles TTL automatically, no cleanup needed")
        return 0

    def get_cache_info(self) -> Dict[str, Any]:
        if self._fallback_repo:
            info = self._fallback_repo.get_cache_info()
            info["fallback_available"] = True
            return info
        try:
            info = self._redis_client.get_info()
            info.update(
                {
                    "backend": "redis",
                    "default_ttl": self._default_ttl,
                    "fallback_available": False,
                    "supports_bulk_operations": True,
                    "supports_pattern_operations": True,
                    "statistics_enabled": True,
                }
            )
            return info
        except Exception as e:
            self.logger.error(f"Error getting cache info: {e}")
            return {
                "backend": "redis",
                "default_ttl": self._default_ttl,
                "error": str(e),
            }

    # --- Bulk ---
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[T]]:
        if self._fallback_repo:
            return await self._fallback_repo.get_many(keys)
        try:
            pipe = await self._redis_client.pipeline()
            for key in keys:
                pipe.get(key)
            raw = await pipe.execute()
            result: Dict[str, Optional[T]] = {}
            for i, key in enumerate(keys):
                v = raw[i] if i < len(raw) else None
                result[key] = v
                if v is not None:
                    self._stats.hits += 1
                else:
                    self._stats.misses += 1
            self._stats.bulk_operations += 1
            self.logger.debug(f"Redis bulk get for {len(keys)} keys")
            return result
        except Exception as e:
            self.logger.error(f"Error in Redis bulk get: {e}")
            return {k: await self.get_by_key(k) for k in keys}

    async def set_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> None:
        if self._fallback_repo:
            await self._fallback_repo.set_many(items, ttl_seconds)
            return
        try:
            pipe = await self._redis_client.pipeline()
            ttl = ttl_seconds or self._default_ttl
            for key, entity in items.items():
                pipe.set(key, entity, ttl_seconds=ttl)
            await pipe.execute()
            self._stats.sets += len(items)
            self._stats.bulk_operations += 1
            self.logger.debug(f"Redis bulk set for {len(items)} items (TTL: {ttl}s)")
        except Exception as e:
            self.logger.error(f"Error in Redis bulk set: {e}")
            for k, v in items.items():
                await self.set_by_key(k, v, ttl_seconds)

    async def delete_many(self, keys: List[str]) -> int:
        if self._fallback_repo:
            return await self._fallback_repo.delete_many(keys)
        if not keys:
            return 0
        try:
            n = 0
            for key in keys:
                if await self._redis_client.delete(key):
                    n += 1
            self._stats.deletes += n
            self._stats.bulk_operations += 1
            self.logger.debug(f"Redis bulk delete: {n}/{len(keys)} keys")
            return n
        except Exception as e:
            self.logger.error(f"Error in Redis bulk delete: {e}")
            return sum(1 for k in keys if await self.delete_by_key(k))

    # --- Pattern ---
    async def get_by_pattern(self, pattern: str) -> Dict[str, T]:
        if self._fallback_repo:
            return await self._fallback_repo.get_by_pattern(pattern)
        try:
            ks = await self._redis_client.keys(pattern)
            if not ks:
                return {}
            many = await self.get_many(ks)
            return {k: v for k, v in many.items() if v is not None}
        except Exception as e:
            self.logger.error(f"Error in Redis pattern get: {e}")
            return {}

    async def delete_by_pattern(self, pattern: str) -> int:
        if self._fallback_repo:
            return await self._fallback_repo.delete_by_pattern(pattern)
        try:
            ks = await self._redis_client.keys(pattern)
            if not ks:
                return 0
            return await self.delete_many(ks)
        except Exception as e:
            self.logger.error(f"Error in Redis pattern delete: {e}")
            return 0

    async def count_by_pattern(self, pattern: str) -> int:
        if self._fallback_repo:
            return await self._fallback_repo.count_by_pattern(pattern)
        try:
            return len(await self._redis_client.keys(pattern))
        except Exception as e:
            self.logger.error(f"Error in Redis pattern count: {e}")
            return 0

    # --- Warming ---
    async def warm_cache(self, data_loader: Callable[[], Dict[str, T]]) -> int:
        try:
            data = data_loader()
            await self.set_many(data, self._default_ttl)
            self.logger.info(f"Redis cache warmed with {len(data)} items")
            return len(data)
        except Exception as e:
            self.logger.error(f"Error warming Redis cache: {e}")
            return 0

    async def preload_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> int:
        await self.set_many(items, ttl_seconds)
        self.logger.info(f"Preloaded {len(items)} items into Redis cache")
        return len(items)

    # --- Stats ---
    async def get_cache_stats(self) -> Dict[str, Any]:
        if self._fallback_repo:
            return await self._fallback_repo.get_cache_stats()
        try:
            d = self._stats.to_dict()
            info = await self._redis_client.info("memory")
            if isinstance(info, dict):
                d["redis_memory_used"] = info.get("used_memory", 0)
                d["redis_memory_peak"] = info.get("used_memory_peak", 0)
                d["redis_connected_clients"] = info.get("connected_clients", 0)
            d["total_keys"] = await self._redis_client.dbsize()
            return d
        except Exception as e:
            self.logger.error(f"Error getting Redis cache stats: {e}")
            return self._stats.to_dict()

    async def get_memory_usage(self) -> Dict[str, Any]:
        if self._fallback_repo:
            return await self._fallback_repo.get_memory_usage()
        try:
            info = await self._redis_client.info("memory")
            if not isinstance(info, dict):
                return {"total_memory_bytes": 0, "backend": "redis"}
            return {
                "total_memory_bytes": info.get("used_memory", 0),
                "peak_memory_bytes": info.get("used_memory_peak", 0),
                "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio", 1.0),
                "used_memory_rss": info.get("used_memory_rss", 0),
                "used_memory_dataset": info.get("used_memory_dataset", 0),
                "used_memory_overhead": info.get("used_memory_overhead", 0),
                "total_keys": await self._redis_client.dbsize(),
                "backend": "redis",
            }
        except Exception as e:
            self.logger.error(f"Error getting Redis memory usage: {e}")
            return {"total_memory_bytes": 0, "backend": "redis", "error": str(e)}
