"""Cache repository interface and supporting types.

Defines ICacheRepository (key-value cache with TTL, bulk, pattern, and stats)
plus CacheStats and CacheOperation.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class ICacheRepository(ABC, Generic[T]):
    """Repository interface for key-value cache with TTL, bulk, pattern, and stats."""

    # --- Single-key ---
    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[T]:
        """Get entity by key."""
        pass

    @abstractmethod
    async def set_by_key(
        self, key: str, entity: T, ttl_seconds: Optional[int] = None
    ) -> T:
        """Set entity by key with optional TTL."""
        pass

    @abstractmethod
    async def set_with_ttl(self, key: str, entity: T, ttl_seconds: int) -> T:
        """Set entity by key with TTL."""
        pass

    @abstractmethod
    async def delete_by_key(self, key: str) -> bool:
        """Delete entity by key."""
        pass

    @abstractmethod
    async def exists_by_key(self, key: str) -> bool:
        """Check if entity exists by key."""
        pass

    @abstractmethod
    async def get_all(self) -> Dict[str, T]:
        """Get all entities as key-value pairs."""
        pass

    @abstractmethod
    async def get_all_keys(self) -> List[str]:
        """Get all keys."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total entities."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all entities."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired entries and return count of cleaned entries."""
        pass

    @abstractmethod
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        pass

    # --- Bulk ---
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[T]]:
        """Get multiple entities by keys efficiently."""
        pass

    @abstractmethod
    async def set_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> None:
        """Set multiple entities efficiently."""
        pass

    @abstractmethod
    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple entities, return count deleted."""
        pass

    # --- Pattern ---
    @abstractmethod
    async def get_by_pattern(self, pattern: str) -> Dict[str, T]:
        """Get all entities matching key pattern."""
        pass

    @abstractmethod
    async def delete_by_pattern(self, pattern: str) -> int:
        """Delete all entities matching pattern."""
        pass

    @abstractmethod
    async def count_by_pattern(self, pattern: str) -> int:
        """Count entities matching pattern."""
        pass

    # --- Warming ---
    @abstractmethod
    async def warm_cache(self, data_loader: Callable[[], Dict[str, T]]) -> int:
        """Bulk load cache from data source."""
        pass

    @abstractmethod
    async def preload_many(
        self, items: Dict[str, T], ttl_seconds: Optional[int] = None
    ) -> int:
        """Preload multiple items efficiently."""
        pass

    # --- Stats ---
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics including hit/miss ratios."""
        pass

    @abstractmethod
    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        pass


class CacheOperation:
    """Represents a single cache operation for batch processing."""

    def __init__(
        self,
        operation: str,
        key: str,
        value: Optional[Any] = None,
        ttl: Optional[int] = None,
    ) -> None:
        self.operation = operation  # "get", "set", "delete"
        self.key = key
        self.value = value
        self.ttl = ttl

    def __repr__(self) -> str:
        return f"CacheOperation(operation={self.operation}, key={self.key})"


class CacheStats:
    """Cache statistics data structure."""

    def __init__(self) -> None:
        self.hits: int = 0
        self.misses: int = 0
        self.sets: int = 0
        self.deletes: int = 0
        self.bulk_operations: int = 0
        self.total_keys: int = 0
        self.memory_usage_bytes: int = 0
        self.hit_ratio: float = 0.0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    def calculate_hit_ratio(self) -> float:
        if self.total_requests == 0:
            return 0.0
        self.hit_ratio = self.hits / self.total_requests
        return self.hit_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "bulk_operations": self.bulk_operations,
            "total_keys": self.total_keys,
            "memory_usage_bytes": self.memory_usage_bytes,
            "hit_ratio": self.calculate_hit_ratio(),
            "total_requests": self.total_requests,
        }
