"""
Integration with existing modelswitch infrastructure.

This module provides integration points with the existing infrastructure
including dependency injection, Redis clients, and configuration management
for the KPI store system.
"""

from typing import Any, Dict, Optional

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from .factory import KPIStoreFactory
from .interfaces import IKPIStore
from .models import KPIStoreConfig

logger = get_logger(__name__)


class KPIStoreIntegration:
    """Integration helper for KPI store with existing infrastructure."""

    @staticmethod
    def create_from_container(container: Any) -> IKPIStore:
        """
        Create KPI store using dependency injection container.

        Args:
            container: Dependency injection container

        Returns:
            Configured KPI store instance
        """
        try:
            # Get Redis client for metrics use case
            redis_client = None
            if hasattr(container, "redis_metrics_client"):
                redis_client = container.redis_metrics_client()
            elif hasattr(container, "redis_client"):
                redis_client = container.redis_client()

            # Get settings if available
            settings = None
            if hasattr(container, "settings"):
                settings = container.settings

            # Create configuration
            KPIStoreIntegration._create_config_from_settings(settings)

            # Determine backend based on Redis availability
            if redis_client:
                logger.info("Creating Redis-backed KPI store")
                return KPIStoreFactory.create_redis_kpi_store(redis_client)
            else:
                logger.info("Creating in-memory KPI store (Redis not available)")
                return KPIStoreFactory.create_in_memory_kpi_store()

        except Exception as e:
            logger.error(f"Error creating metric store from container: {e}")
            # Fallback to in-memory KPI store
            return KPIStoreFactory.create_in_memory_kpi_store()

    @staticmethod
    def _create_config_from_settings(settings: Optional[Any]) -> KPIStoreConfig:
        """Create metric store config from application settings."""
        config = KPIStoreConfig()

        if settings:
            # Extract relevant settings
            if hasattr(settings, "redis_enabled") and settings.redis_enabled:
                config.default_raw_backend = "redis"
                config.default_final_backend = "redis"

            # Set key prefix based on environment or app name
            if hasattr(settings, "environment"):
                config.redis_key_prefix = f"modelswitch:{settings.environment}:metrics:"

            # Performance settings
            if hasattr(settings, "kpi_store_batch_size"):
                config.batch_size = settings.kpi_store_batch_size

            if hasattr(settings, "kpi_store_cleanup_interval"):
                config.cleanup_interval_seconds = settings.kpi_store_cleanup_interval

        return config

    @staticmethod
    def register_with_container(container: Any, metric_store: IKPIStore) -> None:
        """
        Register KPI store with dependency injection container.

        Args:
            container: Dependency injection container
            metric_store: KPI store instance to register
        """
        try:
            from dependency_injector import providers

            # Register as singleton
            if hasattr(container, "kpi_store"):
                logger.warning(
                    "KPI store already registered in container, overriding..."
                )

            # Add KPI store provider
            container.kpi_store = providers.Singleton(lambda: metric_store)

            logger.info("Registered KPI store with dependency injection container")

        except Exception as e:
            logger.error(f"Error registering KPI store with container: {e}")

    @staticmethod
    def create_redis_client_for_metrics(
        infrastructure_lifecycle: Any,
    ) -> Optional[RedisClient]:
        """
        Create Redis client specifically for metrics using infrastructure lifecycle.

        Args:
            infrastructure_lifecycle: Infrastructure lifecycle manager

        Returns:
            Redis client for metrics or None if not available
        """
        try:
            if hasattr(infrastructure_lifecycle, "get_redis_client_for_use_case"):
                return infrastructure_lifecycle.get_redis_client_for_use_case("metrics")
            elif hasattr(infrastructure_lifecycle, "get_redis_client"):
                return infrastructure_lifecycle.get_redis_client()
            else:
                logger.warning("Infrastructure lifecycle does not provide Redis client")
                return None

        except Exception as e:
            logger.error(f"Error creating Redis client for metrics: {e}")
            return None


def setup_kpi_store_integration(
    container: Any, infrastructure_lifecycle: Optional[Any] = None
) -> IKPIStore:
    """
    Set up KPI store integration with existing infrastructure.

    Args:
        container: Dependency injection container
        infrastructure_lifecycle: Infrastructure lifecycle manager (optional)

    Returns:
        Configured and registered KPI store instance
    """
    try:
        # Create Redis client if infrastructure lifecycle is provided
        redis_client = None
        if infrastructure_lifecycle:
            redis_client = KPIStoreIntegration.create_redis_client_for_metrics(
                infrastructure_lifecycle
            )

        # Create KPI store
        if redis_client:
            metric_store = KPIStoreFactory.create_redis_kpi_store(redis_client)
        else:
            metric_store = KPIStoreIntegration.create_from_container(container)

        # Register with container
        KPIStoreIntegration.register_with_container(container, metric_store)

        logger.info("KPI store integration setup complete")
        return metric_store

    except Exception as e:
        logger.error(f"Error setting up KPI store integration: {e}")
        # Return fallback KPI store
        fallback_store = KPIStoreFactory.create_in_memory_kpi_store()
        try:
            KPIStoreIntegration.register_with_container(container, fallback_store)
        except Exception:
            pass  # Ignore registration errors for fallback
        return fallback_store


# Convenience function for common setup patterns
def get_kpi_store_from_app_container() -> Optional[IKPIStore]:
    """
    Get KPI store from the main app container.

    Returns:
        KPI store instance or None if not available
    """
    try:
        # Import here to avoid circular dependencies
        from app.containers import container

        if hasattr(container, "kpi_store"):
            return container.kpi_store()
        else:
            logger.warning("KPI store not found in app container")
            return None

    except ImportError:
        logger.warning("App container not available")
        return None
    except Exception as e:
        logger.error(f"Error getting KPI store from app container: {e}")
        return None


def create_kpi_store_for_module(
    module_name: str,
    redis_client: Optional[RedisClient] = None,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> IKPIStore:
    """
    Create a KPI store instance for a specific module.

    Args:
        module_name: Name of the module (used for key prefixing)
        redis_client: Redis client to use (optional)
        config_overrides: Configuration overrides

    Returns:
        KPI store instance configured for the module
    """
    try:
        # Create base config
        if redis_client:
            config = KPIStoreConfig(
                default_raw_backend="redis",
                default_final_backend="redis",
                redis_key_prefix=f"modelswitch:{module_name}:kpi:",
            )
        else:
            config = KPIStoreConfig(
                default_raw_backend="in_memory",
                default_final_backend="in_memory",
            )

        # Apply overrides
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Create KPI store
        return KPIStoreFactory.create_kpi_store(config, redis_client)

    except Exception as e:
        logger.error(f"Error creating KPI store for module {module_name}: {e}")
        return KPIStoreFactory.create_in_memory_kpi_store()


# Integration with existing metrics system
async def bridge_to_unified_metrics(
    metric_store: IKPIStore, module_name: str = "kpi_store"
) -> None:
    """
    Bridge metric store metrics to the unified metrics system.

    Args:
        metric_store: Metric store instance
        module_name: Module name for metrics registration
    """
    try:
        from common_utils.metrics import track_metric_async

        # Get system stats
        stats = await metric_store.get_system_stats()

        # Bridge key metrics
        await track_metric_async(
            module_name,
            "gauge",
            "total_metrics",
            value=len(await metric_store.list_metrics()),
        )

        await track_metric_async(
            module_name,
            "counter",
            "operations_total",
            value=stats.get("total_metrics_recorded", 0),
        )

        await track_metric_async(
            module_name,
            "counter",
            "computations_total",
            value=stats.get("total_computations", 0),
        )

        await track_metric_async(
            module_name, "counter", "errors_total", value=stats.get("errors", 0)
        )

        # Derived metrics stats
        derived_stats = stats.get("derived_metrics", {})
        if derived_stats:
            await track_metric_async(
                module_name,
                "gauge",
                "derived_metrics_total",
                value=derived_stats.get("total_derived_metrics", 0),
            )

            await track_metric_async(
                module_name,
                "gauge",
                "derived_metrics_active",
                value=derived_stats.get("active_metrics", 0),
            )

        logger.debug(
            f"Bridged metric store metrics to unified system for module: {module_name}"
        )

    except Exception as e:
        logger.error(f"Error bridging metrics to unified system: {e}")


# Lifecycle integration
class KPIStoreLifecycle:
    """Lifecycle management for metric store integration."""

    def __init__(self, metric_store: IKPIStore) -> None:
        self.metric_store = metric_store
        self.logger = logger

    async def startup(self) -> None:
        """Startup tasks for metric store."""
        try:
            logger.info("Starting up metric store...")

            # Perform health check
            health = await self.metric_store.health_check()
            if health["status"] != "healthy":
                logger.warning(f"Metric store health check failed: {health}")

            # Start any background tasks (already handled in KPIStore.__init__)

            logger.info("Metric store startup complete")

        except Exception as e:
            logger.error(f"Error during KPI store startup: {e}")

    async def shutdown(self) -> None:
        """Shutdown tasks for KPI store."""
        try:
            logger.info("Shutting down KPI store...")

            # Shutdown the KPI store
            if hasattr(self.kpi_store, "shutdown"):
                await self.kpi_store.shutdown()

            logger.info("KPI store shutdown complete")

        except Exception as e:
            logger.error(f"Error during KPI store shutdown: {e}")


def add_kpi_store_to_lifecycle(lifecycle_manager: Any, metric_store: IKPIStore) -> None:
    """
    Add KPI store to application lifecycle management.

    Args:
        lifecycle_manager: Application lifecycle manager
        metric_store: KPI store instance
    """
    try:
        kpi_store_lifecycle = KPIStoreLifecycle(metric_store)

        # Register startup and shutdown handlers
        if hasattr(lifecycle_manager, "add_startup_handler"):
            lifecycle_manager.add_startup_handler(kpi_store_lifecycle.startup)

        if hasattr(lifecycle_manager, "add_shutdown_handler"):
            lifecycle_manager.add_shutdown_handler(kpi_store_lifecycle.shutdown)

        logger.info("Added KPI store to application lifecycle")

    except Exception as e:
        logger.error(f"Error adding KPI store to lifecycle: {e}")
