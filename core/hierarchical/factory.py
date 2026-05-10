"""Factory for creating hierarchical unified data services.

This module provides factory functions for creating hierarchical services
from configuration files, with support for different hierarchy types.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from .service import HierarchicalUnifiedService
from .interfaces import HierarchyConfig, NodeConfig


class HierarchicalServiceFactory:
    """Factory for creating hierarchical unified data services."""
    
    def __init__(self, config_directory: str = "./config/hierarchies"):
        """Initialize factory with configuration directory."""
        self.config_directory = Path(config_directory)
    
    def create_service(
        self,
        config: HierarchyConfig,
        data_source: Optional[Any] = None,
        cache_repository: Optional[Any] = None,
        event_service: Optional[Any] = None,
    ) -> HierarchicalUnifiedService:
        """
        Create a hierarchical unified data service from configuration.
        
        Args:
            config: Hierarchy configuration
            data_source: Data source implementation
            cache_repository: Cache repository
            event_service: Event broadcast service
            
        Returns:
            Configured HierarchicalUnifiedService instance
        """
        return HierarchicalUnifiedService(
            data_source=data_source,
            config=config,
            cache_repository=cache_repository,
            event_service=event_service,
        )
    
    def load_from_config(
        self,
        config_name: str,
    ) -> Optional[HierarchicalUnifiedService]:
        """
        Load hierarchy configuration from YAML file and create service.
        
        Args:
            config_name: Name of the hierarchy configuration
            config_name: Name of the hierarchy configuration
            
        Returns:
            HierarchicalUnifiedService instance or None if config not found
        """
        config_path = self.config_directory / f"{config_name}.yaml"
        
        if not config_path.exists():
            return None
        
        try:
            with open(config_path, 'r') as f:
                import yaml
                config_data = yaml.safe_load(f)
                
            hierarchy_config = HierarchyConfig(**config_data)
            return self.create_service(hierarchy_config)
            
        except Exception as e:
            # Log error but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading hierarchy config {config_name}: {e}")
            return None
    
    def list_available_configs(self) -> List[str]:
        """List all available hierarchy configuration files."""
        configs = []
        
        if not self.config_directory.exists():
            return configs
        
        try:
            for file_path in self.config_directory.glob("*.yaml"):
                configs.append(file_path.stem)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing configs: {e}")
        
        return configs
