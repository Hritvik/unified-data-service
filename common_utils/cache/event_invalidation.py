"""Event-driven cache wrapper for distributed invalidation."""

from typing import Any, Callable, Dict, List, Optional, TypeVar

from common_utils.work_in_progress.events import EventBroadcastService, EventType
from common_utils.logger import get_logger

from .interfaces import ICacheRepository

T = TypeVar("T")
logger = get_logger(__name__)


class EventDrivenCache(ICacheRepository[T]):
    """
    Wraps an ICacheRepository and broadcasts cache invalidation events
    on writes for cross-pod invalidation.
    """

    def __init__(
        self,
        base_repository: ICacheRepository[T],
        event_service: Optional[EventBroadcastService],
        service_name: str,
        event_broadcasting_enabled: bool = False,
    ) -> None:
        self._base_repo = base_repository
        self._event_service = event_service
        self._service_name = service_name
        self._event_broadcasting_enabled = event_broadcasting_enabled
        self.logger = logger

    async def get_by_key(self, key: str) -> Optional[T]:
        return await self._base_repo.get_by_key(key)

    async def exists_by_key(self, key: str) -> bool:
        return await self._base_repo.exists_by_key(key)

    async def get_all(self) -> Dict[str, T]:
        return await self._base_repo.get_all()

    async def get_all_keys(self) -> List[str]:
        return await self._base_repo.get_all_keys()

    async def count(self) -> int:
        return await self._base_repo.count()

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[T]]:
        return await self._base_repo.get_many(keys)

    async def get_by_pattern(self, pattern: str) -> Dict[str, T]:
        return await self._base_repo.get_by_pattern(pattern)

    async def count_by_pattern(self, pattern: str) -> int:
        return await self._base_repo.count_by_pattern(pattern)

    async def get_cache_stats(self) -> Dict[str, Any]:
        return await self._base_repo.get_cache_stats()

    async def get_memory_usage(self) -> Dict[str, Any]:
        return await self._base_repo.get_memory_usage()

    def get_cache_info(self) -> Dict[str, Any]:
        info = self._base_repo.get_cache_info()
        info.update(
            {
                "event_aware": True,
                "service_name": self._service_name,
                "event_invalidation_enabled": self._event_broadcasting_enabled,
            }
        )
        return info

    def enable_event_broadcasting(self) -> None:
        self._event_broadcasting_enabled = True
        self.logger.info("Event broadcasting enabled")

    def disable_event_broadcasting(self) -> None:
        self._event_broadcasting_enabled = False
        self.logger.info("Event broadcasting disabled")

    def is_event_broadcasting_enabled(self) -> bool:
        return self._event_broadcasting_enabled

    async def cleanup_expired(self) -> int:
        return await self._base_repo.cleanup_expired()

    async def set_by_key(
        self, key: str, entity: T, ttl_seconds: Optional[int] = None
    ) -> T:
        result = await self._base_repo.set_by_key(key, entity, ttl_seconds)
        await self._broadcast("set", [key])
        return result

    async def set_with_ttl(self, key: str, entity: T, ttl_seconds: int) -> T:
        result = await self._base_repo.set_with_ttl(key, entity, ttl_seconds)
        await self._broadcast("set", [key])
        return result

    async def delete_by_key(self, key: str) -> bool:
        ok = await self._base_repo.delete_by_key(key)
        if ok:
            await self._broadcast("delete", [key])
        return ok

    async def clear(self) -> None:
        await self._base_repo.clear()
        await self._broadcast("clear", [])

    async def set_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> None:
        await self._base_repo.set_many(items, ttl_seconds)
        await self._broadcast("set_many", list(items.keys()))

    async def delete_many(self, keys: List[str]) -> int:
        n = await self._base_repo.delete_many(keys)
        if n > 0:
            await self._broadcast("delete_many", keys)
        return n

    async def delete_by_pattern(self, pattern: str) -> int:
        n = await self._base_repo.delete_by_pattern(pattern)
        if n > 0:
            await self._broadcast("delete_pattern", [], {"pattern": pattern})
        return n

    async def warm_cache(self, data_loader: Callable[[], Dict[str, T]]) -> int:
        n = await self._base_repo.warm_cache(data_loader)
        if n > 0:
            await self._broadcast("warm_cache", [], {"count": n})
        return n

    async def preload_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> int:
        n = await self._base_repo.preload_many(items, ttl_seconds)
        if n > 0:
            await self._broadcast("preload", list(items.keys()))
        return n

    async def invalidate_and_broadcast(self, keys: List[str]) -> None:
        await self._base_repo.delete_many(keys)
        await self._broadcast("invalidate", keys)

    async def refresh_and_broadcast(self) -> None:
        await self._base_repo.clear()
        await self._broadcast("refresh", [])

    async def _broadcast(
        self, action: str, keys: List[str], metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if not self._event_broadcasting_enabled:
            return
        if self._event_service is None:
            return
        try:
            payload: Dict[str, Any] = {
                "service_name": self._service_name,
                "action": action,
                "keys": keys,
            }
            if metadata:
                payload.update(metadata)
            await self._event_service.broadcast_event_by_type(
                EventType.CACHE_REFRESH_SERVICE, payload
            )
            self.logger.debug(
                f"Broadcasted cache event: {self._service_name}, {action}, {len(keys)} keys"
            )
        except Exception as e:
            self.logger.error(f"Error broadcasting cache event: {e}")
