"""Cache infrastructure: key-value cache, TTL mixin, and event invalidation."""

from .event_invalidation import EventDrivenCache
from .factory import CacheFactory
from .interfaces import CacheOperation, CacheStats, ICacheRepository
from .memory import InMemoryCacheRepository
from .metrics import register_cache_metrics
from .mixin import CacheMixin
from .redis_backend import RedisCacheRepository

register_cache_metrics()

__all__ = [
    "CacheMixin",
    "CacheFactory",
    "CacheOperation",
    "CacheStats",
    "EventDrivenCache",
    "ICacheRepository",
    "InMemoryCacheRepository",
    "RedisCacheRepository",
]
