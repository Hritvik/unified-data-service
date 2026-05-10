"""Factory for creating cache repositories."""

from typing import Callable, Optional, TypeVar

from common_utils.work_in_progress.events import EventBroadcastService
from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from .event_invalidation import EventDrivenCache
from .interfaces import ICacheRepository
from .memory import InMemoryCacheRepository
from .redis_backend import RedisCacheRepository

T = TypeVar("T")
logger = get_logger(__name__)


class CacheFactory:
    """Factory for cache repositories."""

    @staticmethod
    def create_in_memory_repository(
        key_extractor: Callable[[T], str],
        default_ttl_seconds: Optional[int] = None,
        cache_name: Optional[str] = None,
    ) -> InMemoryCacheRepository[T]:
        """Create an in-memory cache repository."""
        logger.info("Creating in-memory cache repository")
        return InMemoryCacheRepository[T](
            key_extractor=key_extractor,
            default_ttl_seconds=default_ttl_seconds,
            cache_name=cache_name,
        )

    @staticmethod
    def create_redis_repository(
        key_extractor: Callable[[T], str],
        redis_client: RedisClient,
        default_ttl_seconds: Optional[int] = None,
        cache_name: Optional[str] = None,
    ) -> RedisCacheRepository[T]:
        """Create a Redis cache repository."""
        logger.info("Creating Redis cache repository")
        return RedisCacheRepository[T](
            key_extractor=key_extractor,
            redis_client=redis_client,
            default_ttl_seconds=default_ttl_seconds,
            cache_name=cache_name,
        )

    @staticmethod
    def create_unified_cache_repository(
        entity_type: type[T],
        key_extractor: Callable[[T], str],
        backend: str = "redis",
        redis_client: Optional[RedisClient] = None,
        event_service: Optional[EventBroadcastService] = None,
        key_prefix: str = "",
        default_ttl_seconds: Optional[int] = None,
        enable_bulk_operations: bool = True,
        enable_event_invalidation: bool = True,
        cache_name: Optional[str] = None,
    ) -> ICacheRepository[T]:
        """Create cache repository for unified architecture, optionally with event invalidation."""
        name = cache_name or entity_type.__name__.lower()
        logger.info(
            f"Creating unified cache repository for {entity_type.__name__} (backend: {backend})"
        )
        if backend == "redis" and redis_client is not None:
            base = CacheFactory.create_redis_repository(
                key_extractor=key_extractor,
                redis_client=redis_client,
                default_ttl_seconds=default_ttl_seconds,
                cache_name=name,
            )
        else:
            if backend == "redis":
                logger.warning("Redis client not provided, falling back to in-memory")
            base = CacheFactory.create_in_memory_repository(
                key_extractor=key_extractor,
                default_ttl_seconds=default_ttl_seconds,
                cache_name=name,
            )
        if enable_event_invalidation and event_service:
            logger.info("Wrapping cache with event-driven invalidation")
            return EventDrivenCache[T](
                base_repository=base,
                event_service=event_service,
                service_name=entity_type.__name__.lower(),
                event_broadcasting_enabled=False,
            )
        return base

    @staticmethod
    def create_cache_repository_from_config(
        config: dict,
        entity_type: type[T],
        key_extractor: Callable[[T], str],
        redis_client: Optional[RedisClient] = None,
        event_service: Optional[EventBroadcastService] = None,
    ) -> ICacheRepository[T]:
        """Create cache repository from configuration dictionary."""
        return CacheFactory.create_unified_cache_repository(
            entity_type=entity_type,
            key_extractor=key_extractor,
            backend=config.get("cache_backend", "redis"),
            redis_client=redis_client,
            event_service=event_service,
            key_prefix=config.get("cache_key_prefix", ""),
            default_ttl_seconds=config.get("cache_ttl"),
            enable_bulk_operations=config.get("enable_bulk_operations", True),
            enable_event_invalidation=config.get("enable_event_invalidation", True),
        )

    @staticmethod
    def create_service_cache_repository(
        service_name: str,
        entity_type: type[T],
        key_extractor: Callable[[T], str],
        backend: str = "redis",
        redis_client: Optional[RedisClient] = None,
        event_service: Optional[EventBroadcastService] = None,
        default_ttl_seconds: int = 300,
    ) -> ICacheRepository[T]:
        """Create cache repository for a service with key prefix."""

        def prefixed(e: T) -> str:
            return f"{service_name}:{key_extractor(e)}"

        return CacheFactory.create_unified_cache_repository(
            entity_type=entity_type,
            key_extractor=prefixed,
            backend=backend,
            redis_client=redis_client,
            event_service=event_service,
            key_prefix=f"{service_name}:",
            default_ttl_seconds=default_ttl_seconds,
            enable_bulk_operations=True,
            enable_event_invalidation=True,
            cache_name=service_name,
        )
