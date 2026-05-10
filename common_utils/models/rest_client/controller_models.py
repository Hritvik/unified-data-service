"""
Controller request/response models for REST Client gateway endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common_utils.models.rest_client.caller_config_models import ConfigOverrides


class RestClientProxyRequest(BaseModel):
    """Request to proxy an HTTP call through the rest client."""

    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE, PATCH")
    client_identifier: str = Field(..., description="Service identifier for config lookup")
    path_identifier: str = Field(..., description="Endpoint identifier for config lookup")
    body: Optional[Any] = Field(None, description="Request body (for POST/PUT/PATCH)")
    path_params: Optional[Dict[str, str]] = Field(None, description="Path substitution parameters")
    query_params: Optional[Dict[str, str]] = Field(None, description="Query string parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional HTTP headers")
    config_overrides: Optional[ConfigOverrides] = Field(None, description="Per-request timeout/retry/circuit-breaker overrides")


class RestClientMethodRequest(BaseModel):
    """Request for method-specific proxy endpoints (POST/PUT/PATCH/DELETE)."""

    client_identifier: str = Field(..., description="Service identifier for config lookup")
    path_identifier: str = Field(..., description="Endpoint identifier for config lookup")
    body: Optional[Any] = Field(None, description="Request body")
    path_params: Optional[Dict[str, str]] = Field(None, description="Path substitution parameters")
    query_params: Optional[Dict[str, str]] = Field(None, description="Query string parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional HTTP headers")
    config_overrides: Optional[ConfigOverrides] = Field(None, description="Per-request overrides")


class RestClientProxyResponse(BaseModel):
    """Response from a proxied REST client call."""

    success: bool
    data: Optional[Any] = None
    status_code: Optional[int] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    error: Optional[Dict[str, Any]] = None


class RestClientServiceListResponse(BaseModel):
    """Response listing configured services with full resolved config."""

    success: bool
    services: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    message: Optional[str] = None


class RestClientEndpointListResponse(BaseModel):
    """Response listing endpoints (with full resolved config) for a service."""

    success: bool
    client_identifier: str
    endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    message: Optional[str] = None


class RestClientHealthResponse(BaseModel):
    """Response from REST client health check."""

    status: str
    enabled_sources: Dict[str, bool]
    total_services: int = 0
    source_status: Optional[Dict[str, Any]] = None
