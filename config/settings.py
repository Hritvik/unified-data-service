"""Settings and configuration for Unified Data Service."""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """Database configuration."""
    
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    mongodb_database: str = Field(
        default="unified_data_service",
        description="MongoDB database name"
    )


class CacheSettings(BaseModel):
    """Cache configuration."""
    
    redis_host: str = Field(
        default="localhost",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        description="Redis port"
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password"
    )


class EventServiceSettings(BaseModel):
    """Event service configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable event broadcast service"
    )
    service_name: str = Field(
        default="event_service",
        description="Event service name"
    )


class MetricsSettings(BaseModel):
    """Metrics configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    port: int = Field(
        default=9090,
        description="Metrics port"
    )


class LoggingSettings(BaseModel):
    """Logging configuration."""
    
    level: str = Field(
        default="INFO",
        description="Log level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )


class Settings(BaseModel):
    """Main application settings."""
    
    # Application settings
    app_name: str = Field(
        default="unified-data-service",
        description="Application name"
    )
    version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Service settings
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8080,
        description="Server port"
    )
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    event_service: EventServiceSettings = Field(default_factory=EventServiceSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # Configuration paths
    config_directory: str = Field(
        default="./config/services",
        description="Directory containing service configuration files"
    )
    
    class Config:
        env_prefix = "UDS_"
        env_nested_delimiter = "__"
        
    def __init__(self, **data):
        # Override with environment variables
        env_data = {}
        
        # Database settings
        if "UDS_DATABASE__MONGODB_URI" in os.environ:
            env_data["database"] = {"mongodb_uri": os.environ["UDS_DATABASE__MONGODB_URI"]}
        if "UDS_DATABASE__MONGODB_DATABASE" in os.environ:
            env_data["database"] = env_data.get("database", {})
            env_data["database"]["mongodb_database"] = os.environ["UDS_DATABASE__MONGODB_DATABASE"]
        
        # Cache settings
        if "UDS_CACHE__REDIS_HOST" in os.environ:
            env_data["cache"] = {"redis_host": os.environ["UDS_CACHE__REDIS_HOST"]}
        if "UDS_CACHE__REDIS_PORT" in os.environ:
            env_data["cache"] = env_data.get("cache", {})
            env_data["cache"]["redis_port"] = int(os.environ["UDS_CACHE__REDIS_PORT"])
        if "UDS_CACHE__REDIS_PASSWORD" in os.environ:
            env_data["cache"] = env_data.get("cache", {})
            env_data["cache"]["redis_password"] = os.environ["UDS_CACHE__REDIS_PASSWORD"]
        
        # Event service settings
        if "UDS_EVENT_SERVICE__ENABLED" in os.environ:
            env_data["event_service"] = {"enabled": os.environ["UDS_EVENT_SERVICE__ENABLED"].lower() == "true"}
        
        # Metrics settings
        if "UDS_METRICS__ENABLED" in os.environ:
            env_data["metrics"] = {"enabled": os.environ["UDS_METRICS__ENABLED"].lower() == "true"}
        
        # Application settings
        if "UDS_HOST" in os.environ:
            env_data["host"] = os.environ["UDS_HOST"]
        if "UDS_PORT" in os.environ:
            env_data["port"] = int(os.environ["UDS_PORT"])
        if "UDS_DEBUG" in os.environ:
            env_data["debug"] = os.environ["UDS_DEBUG"].lower() == "true"
        if "UDS_CONFIG_DIRECTORY" in os.environ:
            env_data["config_directory"] = os.environ["UDS_CONFIG_DIRECTORY"]
        
        # Merge environment data with provided data
        merged_data = {**data, **env_data}
        super().__init__(**merged_data)
    
    def get_mongodb_connection_string(self) -> str:
        """Get MongoDB connection string."""
        return self.database.mongodb_uri
    
    def get_redis_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters."""
        params = {
            "host": self.cache.redis_host,
            "port": self.cache.redis_port,
            "db": self.cache.redis_db,
        }
        if self.cache.redis_password:
            params["password"] = self.cache.redis_password
        return params
