from typing import Dict, Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(description="Current health status of the API")
    timestamp: str = Field(description="ISO format timestamp of the health check")
    version: str = Field(default="1.0.0", description="Current API version")


class CacheRefreshResponse(BaseModel):
    """Response model for cache refresh operations."""

    success: bool
    message: str
    details: Dict[str, Any] | None = None
