"""
Factory for creating KPI store instances.
"""

from typing import Optional

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from .interfaces import IKPIStore
from .kpi_store import KPIStore
from .models import KPIStoreConfig

logger = get_logger(__name__)


class KPIStoreFactory:
    """Factory for creating KPI store instances."""

    @staticmethod
    def create_in_memory_kpi_store(
        cleanup_interval_seconds: int = 300,
        max_samples: Optional[int] = None,
        retention_hours: Optional[int] = None,
    ) -> IKPIStore:
        """
        Create an in-memory KPI store.

        Args:
            cleanup_interval_seconds: Interval for background cleanup
            max_samples: Maximum samples per KPI
            retention_hours: Retention time in hours

        Returns:
            Configured in-memory KPI store
        """
        config = KPIStoreConfig(
            default_raw_backend="in_memory",
            default_final_backend="in_memory",
            cleanup_interval_seconds=cleanup_interval_seconds,
        )

        return KPIStore(config=config)

    @staticmethod
    def create_redis_kpi_store(
        redis_client: RedisClient,
        key_prefix: str = "modelswitch:kpi:",
        retention_hours: int = 168,  # 1 week default
        cleanup_interval_seconds: int = 300,
    ) -> IKPIStore:
        """
        Create a Redis-backed KPI store.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis keys
            retention_hours: Retention time in hours
            cleanup_interval_seconds: Interval for background cleanup

        Returns:
            Configured Redis-backed KPI store
        """
        config = KPIStoreConfig(
            default_raw_backend="redis",
            default_final_backend="redis",
            redis_key_prefix=key_prefix,
            cleanup_interval_seconds=cleanup_interval_seconds,
        )

        return KPIStore(config=config, redis_client=redis_client)

    @staticmethod
    def create_kpi_store(
        config: KPIStoreConfig, redis_client: Optional[RedisClient] = None
    ) -> IKPIStore:
        """
        Create a KPI store with custom configuration.

        Args:
            config: KPI store configuration
            redis_client: Redis client (required if using Redis backend)

        Returns:
            Configured KPI store
        """
        return KPIStore(config=config, redis_client=redis_client)

    @staticmethod
    def create_test_kpi_store() -> IKPIStore:
        """
        Create a test KPI store with minimal configuration.

        Returns:
            Test KPI store instance
        """
        config = KPIStoreConfig(
            default_raw_backend="in_memory",
            default_final_backend="in_memory",
            cleanup_interval_seconds=60,
            background_cleanup_enabled=False,
        )
        return KPIStore(config=config)


def create_kpi_store(
    config: KPIStoreConfig, redis_client: Optional[RedisClient] = None
) -> IKPIStore:
    """Convenience function to create a KPI store."""
    return KPIStoreFactory.create_kpi_store(config, redis_client)


def create_test_kpi_store() -> IKPIStore:
    """Convenience function to create a test KPI store."""
    return KPIStoreFactory.create_test_kpi_store()
