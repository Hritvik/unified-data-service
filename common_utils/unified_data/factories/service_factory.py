"""Service factory for creating unified data services from configuration.

This module provides factory functions for creating UnifiedDataService instances
from YAML configuration files.
"""

import importlib
from typing import Any, Dict, Optional, Type, TypeVar

from beanie import Document

from common_utils.cache import CacheFactory
from common_utils.work_in_progress.events import EventBroadcastService
from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from ..data_sources import MongoDBDataSource
from ..interfaces import ServiceConfig
from ..service import UnifiedDataService

T = TypeVar("T", bound=Document)
K = TypeVar("K")

logger = get_logger(__name__)


class ServiceFactory:
    """Factory for creating unified data services from configuration."""

    _service_registry: Dict[str, UnifiedDataService] = {}

    @classmethod
    def create_service(
        cls,
        config: ServiceConfig,
        redis_client: Optional[RedisClient] = None,
        event_service: Optional[EventBroadcastService] = None,
        mongo_client: Optional[Any] = None,
    ) -> UnifiedDataService[T, K]:
        """
        Create a unified data service from configuration.

        Args:
            config: Service configuration
            redis_client: Redis client for caching
            event_service: Event broadcast service
            mongo_client: MongoDB client

        Returns:
            Configured UnifiedDataService instance

        Raises:
            ValueError: If configuration is invalid
            ImportError: If entity type cannot be imported
        """
        logger.info(f"Creating unified data service: {config.name}")

        try:
            # Get entity type
            entity_type = cls._get_entity_type(config.entity_type)

            # Create data source
            data_source = cls._create_data_source(config, entity_type, mongo_client)

            # Create cache repository
            cache_repository = cls._create_cache_repository(
                config, entity_type, redis_client, event_service
            )

            # Create key extractor
            key_extractor = cls._create_key_extractor(config)

            # Create unified service
            service = UnifiedDataService(
                data_source=data_source,
                cache_repository=cache_repository,
                config=config,
                event_service=event_service,
                key_extractor=key_extractor,
            )

            # Inject business logic if specified
            if config.business_logic_class:
                business_class = cls._import_class(config.business_logic_class)
                service.business = business_class(service)

                # Wire up lookup builder if specified
                if config.lookup_optimization and config.lookup_optimization.get(
                    "builder_method"
                ):
                    builder_method = config.lookup_optimization["builder_method"]
                    if hasattr(service.business, builder_method):
                        service._build_lookup_structures = getattr(
                            service.business, builder_method
                        )
                        logger.info(f"Wired up lookup builder method: {builder_method}")

            # Register service
            cls._service_registry[config.name] = service

            logger.info(f"Successfully created unified data service: {config.name}")
            return service

        except Exception as e:
            logger.error(f"Error creating unified data service {config.name}: {e}")
            raise

    @classmethod
    def get_service(cls, service_name: str) -> Optional[UnifiedDataService]:
        """Get a registered service by name."""
        return cls._service_registry.get(service_name)

    @classmethod
    def list_services(cls) -> Dict[str, UnifiedDataService]:
        """Get all registered services."""
        return cls._service_registry.copy()

    @classmethod
    def clear_registry(cls) -> None:
        """Clear the service registry."""
        cls._service_registry.clear()

    @classmethod
    def _get_entity_type(cls, entity_type_name: str) -> Type[T]:
        """Get entity type from string name."""
        try:
            # Try to import from common_utils.models first
            module_name = "common_utils.models"
            module = importlib.import_module(module_name)
            entity_type = getattr(module, entity_type_name)

            if not issubclass(entity_type, Document):
                raise ValueError(
                    f"Entity type {entity_type_name} is not a Beanie Document"
                )

            return entity_type

        except (ImportError, AttributeError):
            # Try other common locations
            for module_name in [
                "common_utils.models.ticket_resolution",
                "common_utils.models.model_bridge",
                "common_utils.models.prompt_registry",
            ]:
                try:
                    module = importlib.import_module(module_name)
                    entity_type = getattr(module, entity_type_name)

                    if issubclass(entity_type, Document):
                        return entity_type

                except (ImportError, AttributeError):
                    continue

            raise ImportError(f"Could not import entity type: {entity_type_name}")

    @classmethod
    def _create_data_source(
        cls, config: ServiceConfig, entity_type: Type[T], mongo_client: Optional[Any]
    ):
        """Create data source based on configuration."""
        data_source_config = config.data_source
        data_source_type = data_source_config.get("type", "mongodb")

        if data_source_type == "mongodb":
            return MongoDBDataSource(
                document_class=entity_type,
                mongo_client=mongo_client,
                key_field=data_source_config.get("key_field", "id"),
            )
        else:
            raise ValueError(f"Unsupported data source type: {data_source_type}")

    @classmethod
    def _create_cache_repository(
        cls,
        config: ServiceConfig,
        entity_type: Type[T],
        redis_client: Optional[RedisClient],
        event_service: Optional[EventBroadcastService],
    ):
        """Create cache repository based on configuration."""

        # Create key extractor for cache
        def cache_key_extractor(entity: T) -> str:
            entity_id = getattr(
                entity, "id", getattr(entity, "_id", str(hash(str(entity))))
            )
            return f"{config.cache_key_prefix}{entity_id}"

        return CacheFactory.create_unified_cache_repository(
            entity_type=entity_type,
            key_extractor=cache_key_extractor,
            backend=config.cache_backend,
            redis_client=redis_client,
            event_service=event_service,
            key_prefix=config.cache_key_prefix,
            default_ttl_seconds=config.cache_ttl,
            enable_bulk_operations=config.enable_bulk_operations,
            enable_event_invalidation=config.enable_event_invalidation,
        )

    @classmethod
    def _create_key_extractor(cls, config: ServiceConfig):
        """Create key extractor function for the service."""

        def key_extractor(entity: T) -> str:
            entity_id = getattr(
                entity, "id", getattr(entity, "_id", str(hash(str(entity))))
            )
            return f"{config.cache_key_prefix}{entity_id}"

        return key_extractor

    @classmethod
    def create_service_from_dict(
        cls,
        config_dict: Dict[str, Any],
        redis_client: Optional[RedisClient] = None,
        event_service: Optional[EventBroadcastService] = None,
        mongo_client: Optional[Any] = None,
    ) -> UnifiedDataService[T, K]:
        """
        Create service from configuration dictionary.

        Args:
            config_dict: Configuration dictionary
            redis_client: Redis client for caching
            event_service: Event broadcast service
            mongo_client: MongoDB client

        Returns:
            Configured UnifiedDataService instance
        """
        config = ServiceConfig(**config_dict)
        return cls.create_service(config, redis_client, event_service, mongo_client)

    @classmethod
    async def warm_all_caches(cls) -> Dict[str, int]:
        """Warm caches for all registered services."""
        results = {}

        for service_name, service in cls._service_registry.items():
            try:
                count = await service.warm_cache()
                results[service_name] = count
                logger.info(f"Warmed cache for {service_name}: {count} items")
            except Exception as e:
                logger.error(f"Error warming cache for {service_name}: {e}")
                results[service_name] = 0

        return results

    @classmethod
    async def health_check_all(cls) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all registered services."""
        results = {}

        for service_name, service in cls._service_registry.items():
            try:
                health = await service.health_check()
                results[service_name] = health
            except Exception as e:
                logger.error(f"Error checking health for {service_name}: {e}")
                results[service_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "service_name": service_name,
                }

        return results

    @classmethod
    async def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all registered services."""
        results = {}

        for service_name, service in cls._service_registry.items():
            try:
                stats = await service.get_service_stats()
                results[service_name] = stats
            except Exception as e:
                logger.error(f"Error getting stats for {service_name}: {e}")
                results[service_name] = {
                    "error": str(e),
                    "service_name": service_name,
                }

        return results

    @classmethod
    def _import_class(cls, class_path: str) -> Type[Any]:
        """Import a class from a string path."""
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing class {class_path}: {e}")
            raise ImportError(f"Could not import class: {class_path}") from e
