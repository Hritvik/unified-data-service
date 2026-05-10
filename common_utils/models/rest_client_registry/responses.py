"""
REST client registry responses module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from common_utils.enums import CircuitBreakerStrategy, RetryStrategyType


class ConnectionPoolConfigInfo(BaseModel):
    """Connection pool configuration information for responses."""

    default_max_per_route: int
    max_total: int


class AuthConfigInfo(BaseModel):
    """Authentication configuration information for responses."""

    key: str
    value: str


class CredentialsConfigInfo(BaseModel):
    """Credentials configuration information for responses."""

    host: str
    auth: List[AuthConfigInfo]


class TimeoutConfigInfo(BaseModel):
    """Timeout configuration information for responses."""

    connection_timeout: int
    request_timeout: int
    socket_timeout: int
    pool_timeout: int
    read_timeout: int
    write_timeout: int


class CircuitBreakerConfigInfo(BaseModel):
    """Circuit breaker configuration information for responses."""

    strategy: CircuitBreakerStrategy
    failure_threshold: int
    recovery_timeout: int
    expected_exceptions: List[str]


class RetryConfigInfo(BaseModel):
    """Retry configuration information for responses."""

    strategy: RetryStrategyType
    max_attempts: int
    wait_seconds: float
    multiplier: float
    max_interval: float
    start_wait: float
    increment: float
    retryable_exceptions: List[str]


class EndpointConfigInfo(BaseModel):
    """Endpoint configuration information for responses."""

    id: str
    service_name: str
    name: str
    path: str
    method: str
    timeout: Optional[TimeoutConfigInfo]
    headers: Dict[str, str]
    path_params: Dict[str, str]
    query_params: Dict[str, str]
    auth: List[AuthConfigInfo]
    circuit_breaker: Optional[CircuitBreakerConfigInfo]
    retry: Optional[RetryConfigInfo]
    created_at: str
    updated_at: str


class ServiceConfigInfo(BaseModel):
    """Service configuration information for responses."""

    id: str
    name: str
    activate_at_startup: bool
    connection_pool: ConnectionPoolConfigInfo
    credentials: Optional[CredentialsConfigInfo]
    headers: Dict[str, str]
    timeout: TimeoutConfigInfo
    circuit_breaker: CircuitBreakerConfigInfo
    retry: RetryConfigInfo
    endpoints: List[EndpointConfigInfo]
    created_at: str
    updated_at: str


# Response models with success wrapper
class ServiceConfigResponse(BaseModel):
    """Response model for service configuration."""

    success: bool = Field(..., description="Success status")
    data: Optional[ServiceConfigInfo] = Field(
        None, description="Service configuration data"
    )
    message: Optional[str] = Field(None, description="Response message")


class ServiceConfigListResponse(BaseModel):
    """Response model for listing service configurations."""

    success: bool = Field(..., description="Success status")
    data: List[ServiceConfigInfo] = Field(
        ..., description="List of service configurations"
    )
    total_count: int = Field(..., description="Total number of services")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    message: Optional[str] = Field(None, description="Response message")


