"""
Cross-module dependency injection container.

This container manages dependencies that are shared across multiple modules,
such as services that need to be accessed by other modules.
"""

from dependency_injector import containers, providers

# Import services from different modules
# These imports are done lazily to avoid circular dependencies


class CrossModuleContainer(containers.DeclarativeContainer):
    """
    Cross-module dependency injection container.

    This container manages dependencies that are shared across multiple modules.
    It provides a centralized way to configure and instantiate cross-module services.
    """

    # Configuration
    config = providers.Configuration()

    # Cross-module services
    # These are defined as providers that can be overridden by specific modules

    # REST Client - provided by rest_client module
    rest_client = providers.Dependency()

    # Model Bridge - provided by model_bridge module
    model_bridge = providers.Dependency()

    # Unified Service Registry - provided by app module.
    # Replaces the legacy rest_client_registry / model_bridge_registry /
    # prompt_registry providers; downstream callers now resolve V2
    # services through ServiceFactory.get_service(...) directly.
    unified_service_registry = providers.Dependency()


# Global cross-module container instance
cross_module_container = CrossModuleContainer()
