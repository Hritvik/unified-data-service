"""
REST client models module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from datetime import datetime
from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

from .http_models import (
    HttpHeaders,
    PathParams,
    QueryParams,
    RequestMetadata,
    ResponseMetadata,
)


class RequestType(str, Enum):
    """Enumeration of request types."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ResponseType(str, Enum):
    """Enumeration of response types."""

    JSON = "json"
    TEXT = "text"
    BYTES = "bytes"
    STREAM = "stream"


T = TypeVar("T")
R = TypeVar("R")


class EndpointMetadata(BaseModel):
    """Metadata for endpoint configuration."""

    service_name: str = Field(..., description="Service name")
    endpoint_name: str = Field(..., description="Endpoint name")
    path: str = Field(..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    description: Optional[str] = Field(default=None, description="Endpoint description")
    version: Optional[str] = Field(default=None, description="API version")
    deprecated: bool = Field(
        default=False, description="Whether endpoint is deprecated"
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if v.upper() not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {v}")
        return v.upper()


class ClientConfig(BaseModel):
    """Configuration for REST client instances."""

    client_identifier: str = Field(..., description="Unique client identifier")
    base_url: str = Field(..., description="Base URL for the client")
    default_headers: HttpHeaders = Field(
        default_factory=HttpHeaders, description="Default headers"
    )
    default_timeout: float = Field(
        default=30.0, description="Default timeout in seconds"
    )
    max_retries: int = Field(default=3, description="Maximum number of retries")
    enable_logging: bool = Field(
        default=True, description="Enable request/response logging"
    )
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    connection_pool_size: int = Field(default=20, description="Connection pool size")

    @field_validator("default_timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Validate max retries."""
        if v < 0:
            raise ValueError("Max retries cannot be negative")
        return v

    @field_validator("connection_pool_size")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Validate connection pool size."""
        if v < 1:
            raise ValueError("Connection pool size must be positive")
        return v


class RestClientRequest(BaseModel, Generic[T]):
    """Model for REST client requests with type safety."""

    client_identifier: str = Field(..., description="Client identifier")
    path_identifier: str = Field(..., description="Path identifier")
    method: RequestType = Field(..., description="HTTP method")
    data: Optional[T] = Field(default=None, description="Request data")
    path_params: PathParams = Field(
        default_factory=PathParams, description="Path parameters"
    )
    query_params: QueryParams = Field(
        default_factory=QueryParams, description="Query parameters"
    )
    headers: HttpHeaders = Field(
        default_factory=HttpHeaders, description="Request headers"
    )
    timeout: Optional[float] = Field(default=None, description="Request timeout")
    response_type: Optional[ResponseType] = Field(
        default=ResponseType.JSON, description="Expected response type"
    )
    fallback: Optional[str] = Field(default=None, description="Fallback function name")
    metadata: Optional[RequestMetadata] = Field(
        default=None, description="Request metadata"
    )

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[float]) -> Optional[float]:
        """Validate timeout."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be positive")
        return v


class RestClientResponse(BaseModel, Generic[R]):
    """Model for REST client responses with type safety."""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[R] = Field(default=None, description="Response data")
    status_code: int = Field(..., description="HTTP status code")
    headers: HttpHeaders = Field(
        default_factory=HttpHeaders, description="Response headers"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    metadata: Optional[ResponseMetadata] = Field(
        default=None, description="Response metadata"
    )

    @field_validator("status_code")
    @classmethod
    def validate_status_code(cls, v: int) -> int:
        """Validate HTTP status code."""
        if not 100 <= v <= 599:
            raise ValueError(f"Invalid HTTP status code: {v}")
        return v


class BatchRequest(BaseModel):
    """Model for batch requests."""

    requests: list[RestClientRequest] = Field(
        ..., description="List of requests to execute"
    )
    parallel: bool = Field(
        default=True, description="Whether to execute requests in parallel"
    )
    max_concurrent: int = Field(default=10, description="Maximum concurrent requests")

    @field_validator("max_concurrent")
    @classmethod
    def validate_max_concurrent(cls, v: int) -> int:
        """Validate max concurrent requests."""
        if v < 1:
            raise ValueError("Max concurrent must be positive")
        return v


class BatchResponse(BaseModel):
    """Model for batch responses."""

    responses: list[RestClientResponse] = Field(..., description="List of responses")
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    total_time_ms: float = Field(
        ..., description="Total execution time in milliseconds"
    )

    @field_validator("total_requests", "successful_requests", "failed_requests")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Validate non-negative integers."""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    @field_validator("total_time_ms")
    @classmethod
    def validate_time(cls, v: float) -> float:
        """Validate total time."""
        if v < 0:
            raise ValueError("Total time cannot be negative")
        return v

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class ClientMetrics(BaseModel):
    """Model for client metrics."""

    client_identifier: str = Field(..., description="Client identifier")
    total_requests: int = Field(default=0, description="Total number of requests")
    successful_requests: int = Field(
        default=0, description="Number of successful requests"
    )
    failed_requests: int = Field(default=0, description="Number of failed requests")
    total_response_time_ms: float = Field(
        default=0.0, description="Total response time in milliseconds"
    )
    average_response_time_ms: float = Field(
        default=0.0, description="Average response time in milliseconds"
    )
    last_request_time: Optional[datetime] = Field(
        default=None, description="Timestamp of last request"
    )
    last_success_time: Optional[datetime] = Field(
        default=None, description="Timestamp of last success"
    )
    last_failure_time: Optional[datetime] = Field(
        default=None, description="Timestamp of last failure"
    )

    @field_validator("total_requests", "successful_requests", "failed_requests")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Validate non-negative integers."""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    @field_validator("total_response_time_ms", "average_response_time_ms")
    @classmethod
    def validate_time(cls, v: float) -> float:
        """Validate time values."""
        if v < 0:
            raise ValueError("Time cannot be negative")
        return v

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class HealthCheckRequest(BaseModel):
    """Model for health check requests."""

    client_identifier: str = Field(..., description="Client identifier to check")
    timeout: float = Field(default=5.0, description="Health check timeout")
    include_metrics: bool = Field(
        default=True, description="Include metrics in response"
    )

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v


class HealthCheckResponse(BaseModel):
    """Model for health check responses."""

    healthy: bool = Field(..., description="Whether the client is healthy")
    client_identifier: str = Field(..., description="Client identifier")
    status_message: str = Field(..., description="Health status message")
    response_time_ms: float = Field(..., description="Health check response time")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    metrics: Optional[ClientMetrics] = Field(
        default=None, description="Client metrics if requested"
    )

    @field_validator("response_time_ms")
    @classmethod
    def validate_response_time(cls, v: float) -> float:
        """Validate response time."""
        if v < 0:
            raise ValueError("Response time cannot be negative")
        return v
