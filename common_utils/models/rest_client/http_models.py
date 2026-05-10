"""
REST client HTTP models module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from datetime import datetime
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator


class HttpHeaders(BaseModel):
    """Model for HTTP headers with validation and convenience methods."""

    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get header value with case-insensitive lookup."""
        for k, v in self.headers.items():
            if k.lower() == key.lower():
                return v
        return default

    def set(self, key: str, value: str) -> None:
        """Set header value."""
        self.headers[key] = value

    def setdefault(self, key: str, value: str) -> str:
        """Set header value if key doesn't exist, return the value."""
        return self.headers.setdefault(key, value)

    def update(self, other: Union[Dict[str, str], "HttpHeaders"]) -> None:
        """Update headers with another dictionary or HttpHeaders object."""
        if isinstance(other, HttpHeaders):
            self.headers.update(other.headers)
        else:
            self.headers.update(other)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return self.headers.copy()


class QueryParams(BaseModel):
    """Model for query parameters with validation and convenience methods."""

    params: Dict[str, str] = Field(default_factory=dict, description="Query parameters")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get parameter value."""
        return self.params.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Set parameter value."""
        self.params[key] = value

    def update(self, other: Union[Dict[str, str], "QueryParams"]) -> None:
        """Update parameters with another dictionary or QueryParams object."""
        if isinstance(other, QueryParams):
            self.params.update(other.params)
        else:
            self.params.update(other)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return self.params.copy()


class PathParams(BaseModel):
    """Model for path parameters with validation and convenience methods."""

    params: Dict[str, str] = Field(default_factory=dict, description="Path parameters")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get parameter value."""
        return self.params.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Set parameter value."""
        self.params[key] = value

    def update(self, other: Union[Dict[str, str], "PathParams"]) -> None:
        """Update parameters with another dictionary or PathParams object."""
        if isinstance(other, PathParams):
            self.params.update(other.params)
        else:
            self.params.update(other)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return self.params.copy()


class TimeoutConfig(BaseModel):
    """Configuration model for HTTP request timeouts."""

    connect: Optional[float] = Field(
        default=None, description="Connection timeout in seconds"
    )
    read: Optional[float] = Field(default=None, description="Read timeout in seconds")
    write: Optional[float] = Field(default=None, description="Write timeout in seconds")
    pool: Optional[float] = Field(default=None, description="Pool timeout in seconds")

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx.Timeout object."""
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool,
        )

    @classmethod
    def from_httpx_timeout(cls, timeout: httpx.Timeout) -> "TimeoutConfig":
        """Create TimeoutConfig from httpx.Timeout object."""
        return cls(
            connect=timeout.connect,
            read=timeout.read,
            write=timeout.write,
            pool=None,  # httpx.Timeout doesn't have pool attribute
        )


class RequestMetadata(BaseModel):
    """Metadata for HTTP requests."""

    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Request URL")
    client_identifier: str = Field(..., description="Client identifier")
    path_identifier: str = Field(..., description="Path identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )
    request_id: Optional[str] = Field(default=None, description="Unique request ID")
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracing"
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if v.upper() not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {v}")
        return v.upper()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        try:
            urlparse(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")


class ResponseMetadata(BaseModel):
    """Metadata for HTTP responses."""

    response_time_ms: float = Field(..., description="Response time in milliseconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: Optional[str] = Field(
        default=None, description="Request ID this response corresponds to"
    )

    @field_validator("response_time_ms")
    @classmethod
    def validate_response_time(cls, v: float) -> float:
        """Validate response time."""
        if v < 0:
            raise ValueError("Response time cannot be negative")
        return v


class HttpResponse(BaseModel):
    """Model for HTTP responses with structured data."""

    status_code: int = Field(..., description="HTTP status code")
    headers: HttpHeaders = Field(
        default_factory=HttpHeaders, description="Response headers"
    )
    body: Optional[Any] = Field(default=None, description="Response body")
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

    def is_success(self) -> bool:
        """Check if response indicates success (2xx status codes)."""
        return 200 <= self.status_code < 300

    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx status codes)."""
        return 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx status codes)."""
        return 500 <= self.status_code < 600

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return {
            "status_code": self.status_code,
            "headers": self.headers.to_dict(),
            "body": self.body,
        }


class HttpRequest(BaseModel):
    """Model for HTTP requests with structured data."""

    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Request URL")
    host: Optional[str] = Field(
        default=None, description="Request host (extracted from URL)"
    )
    path: Optional[str] = Field(
        default=None, description="Request path (extracted from URL)"
    )
    headers: HttpHeaders = Field(
        default_factory=HttpHeaders, description="Request headers"
    )
    query_params: QueryParams = Field(
        default_factory=QueryParams, description="Query parameters"
    )
    path_params: PathParams = Field(
        default_factory=PathParams, description="Path parameters"
    )
    body: Optional[Any] = Field(default=None, description="Request body")
    timeout: Optional[TimeoutConfig] = Field(
        default=None, description="Request timeout configuration"
    )
    metadata: Optional[RequestMetadata] = Field(
        default=None, description="Request metadata"
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if v.upper() not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {v}")
        return v.upper()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        try:
            urlparse(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

    @model_validator(mode="after")
    def extract_host_and_path(self) -> "HttpRequest":
        """Extract host and path from URL if not provided."""
        if self.url and (self.host is None or self.path is None):
            try:
                parsed = urlparse(self.url)
                if self.host is None:
                    self.host = parsed.netloc
                if self.path is None:
                    self.path = parsed.path
            except Exception:
                # If parsing fails, use defaults
                if self.host is None:
                    self.host = "unknown"
                if self.path is None:
                    self.path = "/"
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers.to_dict(),
            "query_params": self.query_params.to_dict(),
            "path_params": self.path_params.to_dict(),
            "body": self.body,
            "timeout": self.timeout,
        }
