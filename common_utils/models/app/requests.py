from pydantic import BaseModel


class CacheRefreshRequest(BaseModel):
    """Request model for cache refresh operations."""

    service_name: str | None = None
    pattern: str | None = None
    refresh_all: bool = False
