"""Feature flags system for gradual migration.

This module provides a centralized way to manage feature flags
for the unified data service migration.
"""

import os
from typing import Any, Dict, Optional
import yaml
from .logger import get_logger

logger = get_logger(__name__)


class FeatureFlags:
    """Centralized feature flags management."""
    
    _flags: Dict[str, Any] = {}
    _loaded = False
    
    @classmethod
    def load_flags(cls, config_path: Optional[str] = None) -> None:
        """Load feature flags from configuration."""
        if cls._loaded:
            return
        
        # Try to load from config file
        if not config_path:
            config_path = os.environ.get(
                "FEATURE_FLAGS_CONFIG",
                "config/feature_flags.yaml"
            )
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    cls._flags = config.get("feature_flags", {})
                    logger.info(f"Loaded feature flags from {config_path}")
            else:
                logger.warning(f"Feature flags config not found at {config_path}, using defaults")
                cls._flags = cls._get_default_flags()
        except Exception as e:
            logger.error(f"Error loading feature flags: {e}")
            cls._flags = cls._get_default_flags()
        
        cls._loaded = True
    
    @classmethod
    def _get_default_flags(cls) -> Dict[str, Any]:
        """Get default feature flags."""
        return {
            # Migration flags
            "UNIFIED_DATA_MICROSERVICE_ENABLED": False,
            "UNIFIED_DATA_MIGRATION_MODE": "embedded",  # "embedded", "microservice", "hybrid"
            "UNIFIED_DATA_FALLBACK_ENABLED": True,
            
            # Service-specific flags
            "PROMPT_TEMPLATE_MICROSERVICE": False,
            "MODEL_REGISTRY_MICROSERVICE": False,
            "FINANCE_SERVICES_MICROSERVICE": False,
            
            # Monitoring flags
            "MIGRATION_LOGGING_ENABLED": True,
            "PERFORMANCE_COMPARISON_ENABLED": True,
            "ERROR_ALERTING_ENABLED": True,
            
            # Safety flags
            "READ_ONLY_MODE": False,
            "SAFE_MIGRATION": True,  # Only migrate if health checks pass
        }
    
    @classmethod
    def is_enabled(cls, flag_name: str, default: bool = False) -> bool:
        """Check if a feature flag is enabled."""
        if not cls._loaded:
            cls.load_flags()
        
        return cls._flags.get(flag_name, default)
    
    @classmethod
    def get_flag(cls, flag_name: str, default: Any = None) -> Any:
        """Get the value of a feature flag."""
        if not cls._loaded:
            cls.load_flags()
        
        return cls._flags.get(flag_name, default)
    
    @classmethod
    def set_flag(cls, flag_name: str, value: Any) -> None:
        """Set a feature flag value at runtime."""
        cls._flags[flag_name] = value
        logger.info(f"Feature flag '{flag_name}' set to {value}")
    
    @classmethod
    def get_all_flags(cls) -> Dict[str, Any]:
        """Get all feature flags."""
        if not cls._loaded:
            cls.load_flags()
        
        return cls._flags.copy()
    
    @classmethod
    def is_migration_enabled(cls) -> bool:
        """Check if unified data migration is enabled."""
        return cls.is_enabled("UNIFIED_DATA_MICROSERVICE_ENABLED")
    
    @classmethod
    def get_migration_mode(cls) -> str:
        """Get migration mode."""
        return cls.get_flag("UNIFIED_DATA_MIGRATION_MODE", "embedded")
    
    @classmethod
    def is_fallback_enabled(cls) -> bool:
        """Check if fallback to embedded mode is enabled."""
        return cls.is_enabled("UNIFIED_DATA_FALLBACK_ENABLED")
    
    @classmethod
    def is_service_migrated(cls, service_name: str) -> bool:
        """Check if a specific service is migrated to microservice."""
        service_flag = f"{service_name.upper().replace('-', '_')}_MICROSERVICE"
        return cls.is_enabled(service_flag)
    
    @classmethod
    def should_log_migration(cls) -> bool:
        """Check if migration logging is enabled."""
        return cls.is_enabled("MIGRATION_LOGGING_ENABLED")
    
    @classmethod
    def should_compare_performance(cls) -> bool:
        """Check if performance comparison is enabled."""
        return cls.is_enabled("PERFORMANCE_COMPARISON_ENABLED")
    
    @classmethod
    def is_safe_migration(cls) -> bool:
        """Check if safe migration mode is enabled."""
        return cls.is_enabled("SAFE_MIGRATION")


# Convenience functions for commonly used flags
def is_microservice_enabled() -> bool:
    """Check if microservice mode is enabled."""
    return FeatureFlags.is_migration_enabled()


def get_migration_mode() -> str:
    """Get current migration mode."""
    return FeatureFlags.get_migration_mode()


def is_service_migrated(service_name: str) -> bool:
    """Check if a specific service is migrated."""
    return FeatureFlags.is_service_migrated(service_name)


def should_fallback() -> bool:
    """Check if fallback is enabled."""
    return FeatureFlags.is_fallback_enabled()


def should_log_migration() -> bool:
    """Check if migration logging is enabled."""
    return FeatureFlags.should_log_migration()
