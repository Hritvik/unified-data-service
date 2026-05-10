"""Embedded sub-document schemas (BaseModel) for REST client registry Beanie docs.

The legacy ``ServiceDocument`` / ``EndpointDocument`` Beanie classes were
dropped along with the legacy ``services`` / ``endpoints`` Mongo collections;
only the nested sub-models survive because ``ServiceDocument`` and
``EndpointDocument`` still embed them verbatim (same field shapes, same
BSON layout).

These sub-models are also re-exported from the ``common_utils.models``
package barrel; either import path is supported.
"""

__all__ = [
    "AuthConfigDocument",
    "CircuitBreakerConfigDocument",
    "ConnectionPoolConfigDocument",
    "CredentialsConfigDocument",
    "RetryConfigDocument",
    "TimeoutConfigDocument",
]

from typing import List

from pydantic import BaseModel, Field

from common_utils.enums import CircuitBreakerStrategy, RetryStrategyType


class ConnectionPoolConfigDocument(BaseModel):
    """Document model for connection pool configuration."""

    default_max_per_route: int = Field(
        default=20, description="Default max connections per route"
    )
    max_total: int = Field(default=20, description="Maximum total connections")


class TimeoutConfigDocument(BaseModel):
    """Document model for timeout configuration."""

    connection_timeout: int = Field(
        default=100, description="Connection timeout in milliseconds"
    )
    request_timeout: int = Field(
        default=100, description="Request timeout in milliseconds"
    )
    socket_timeout: int = Field(
        default=100, description="Socket timeout in milliseconds"
    )
    pool_timeout: int = Field(default=100, description="Pool timeout in milliseconds")
    read_timeout: int = Field(default=100, description="Read timeout in milliseconds")
    write_timeout: int = Field(default=100, description="Write timeout in milliseconds")


class CircuitBreakerConfigDocument(BaseModel):
    """Document model for circuit breaker configuration."""

    strategy: CircuitBreakerStrategy = Field(
        default=CircuitBreakerStrategy.NONE, description="Circuit breaker strategy"
    )
    failure_threshold: int = Field(
        default=5, description="Failure threshold before opening circuit"
    )
    recovery_timeout: int = Field(default=60, description="Recovery timeout in seconds")
    expected_exceptions: List[str] = Field(
        default_factory=list, description="Expected rest_client"
    )


class RetryConfigDocument(BaseModel):
    """Document model for retry configuration."""

    strategy: RetryStrategyType = Field(
        default=RetryStrategyType.NO_RETRY, description="Retry strategy"
    )
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    wait_seconds: float = Field(default=1.0, description="Wait time between retries")
    multiplier: float = Field(
        default=1.0, description="Multiplier for exponential backoff"
    )
    max_interval: float = Field(
        default=10.0, description="Maximum interval between retries"
    )
    start_wait: float = Field(default=1.0, description="Initial wait time")
    increment: float = Field(default=1.0, description="Increment for linear backoff")
    retryable_exceptions: List[str] = Field(
        default_factory=list, description="Retryable rest_client"
    )


class AuthConfigDocument(BaseModel):
    """Document model for authentication configuration."""

    key: str = Field(..., description="Authentication key")
    value: str = Field(..., description="Authentication value")
    type: str = Field(default="header", description="Authentication type")


class CredentialsConfigDocument(BaseModel):
    """Document model for credentials configuration."""

    host: str = Field(default="", description="Host for credentials")
    auth: List[AuthConfigDocument] = Field(
        default_factory=list, description="Authentication configurations"
    )
