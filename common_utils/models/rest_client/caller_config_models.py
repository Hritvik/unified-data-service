"""
Caller configuration override models for REST client.

This module contains models that allow callers to override default configurations
for circuit breaker, retry, and timeout settings on a per-request basis.
"""

from typing import Annotated, Any, Callable, List, Optional

from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema

from common_utils.enums import CircuitBreakerStrategy, RetryStrategyType


class CallerTimeoutConfig(BaseModel):
    """Caller-provided timeout configuration override."""

    connection_timeout: Optional[int] = None
    request_timeout: Optional[int] = None
    socket_timeout: Optional[int] = None
    pool_timeout: Optional[int] = None
    read_timeout: Optional[int] = None
    write_timeout: Optional[int] = None

    def to_httpx_timeout(self) -> Any:
        """Convert to httpx.Timeout object if httpx is available."""
        try:
            import httpx

            return httpx.Timeout(
                connect=self.connection_timeout / 1000.0
                if self.connection_timeout
                else None,
                read=self.read_timeout / 1000.0 if self.read_timeout else None,
                write=self.write_timeout / 1000.0 if self.write_timeout else None,
                pool=self.pool_timeout / 1000.0 if self.pool_timeout else None,
            )
        except ImportError:
            return None


class CallerCircuitBreakerConfig(BaseModel):
    """Caller-provided circuit breaker configuration override."""

    strategy: Optional[CircuitBreakerStrategy] = None
    failure_threshold: Optional[int] = None
    recovery_timeout: Optional[int] = None
    expected_exceptions: Optional[List[str]] = None
    name: Optional[str] = None
    log_state_changes: Optional[bool] = None
    log_failures: Optional[bool] = None


class CallerRetryConfig(BaseModel):
    """Caller-provided retry configuration override."""

    strategy: Optional[RetryStrategyType] = None
    max_attempts: Optional[int] = None
    wait_seconds: Optional[float] = None
    multiplier: Optional[float] = None
    max_interval: Optional[float] = None
    start_wait: Optional[float] = None
    increment: Optional[float] = None
    retryable_exceptions: Optional[List[str]] = None
    # Runtime-only hooks — not representable in OpenAPI (Callable schema).
    retry_predicate: Annotated[
        Optional[Callable[[Exception], bool]],
        SkipJsonSchema(),
    ] = None
    custom_wait_func: Annotated[
        Optional[Callable[[int], float]],
        SkipJsonSchema(),
    ] = None


class ConfigOverrides(BaseModel):
    """Container for all configuration overrides."""

    timeout: Optional[CallerTimeoutConfig] = None
    circuit_breaker: Optional[CallerCircuitBreakerConfig] = None
    retry: Optional[CallerRetryConfig] = None

    def has_any_overrides(self) -> bool:
        """Check if any configuration overrides are provided."""
        return any(
            [
                self.timeout is not None,
                self.circuit_breaker is not None,
                self.retry is not None,
            ]
        )

    def has_timeout_overrides(self) -> bool:
        """Check if timeout overrides are provided."""
        return self.timeout is not None and any(
            [
                self.timeout.connection_timeout is not None,
                self.timeout.request_timeout is not None,
                self.timeout.socket_timeout is not None,
                self.timeout.pool_timeout is not None,
                self.timeout.read_timeout is not None,
                self.timeout.write_timeout is not None,
            ]
        )

    def has_circuit_breaker_overrides(self) -> bool:
        """Check if circuit breaker overrides are provided."""
        return self.circuit_breaker is not None and any(
            [
                self.circuit_breaker.strategy is not None,
                self.circuit_breaker.failure_threshold is not None,
                self.circuit_breaker.recovery_timeout is not None,
                self.circuit_breaker.expected_exceptions is not None,
                self.circuit_breaker.name is not None,
                self.circuit_breaker.log_state_changes is not None,
                self.circuit_breaker.log_failures is not None,
            ]
        )

    def has_retry_overrides(self) -> bool:
        """Check if retry overrides are provided."""
        return self.retry is not None and any(
            [
                self.retry.strategy is not None,
                self.retry.max_attempts is not None,
                self.retry.wait_seconds is not None,
                self.retry.multiplier is not None,
                self.retry.max_interval is not None,
                self.retry.start_wait is not None,
                self.retry.increment is not None,
                self.retry.retryable_exceptions is not None,
                self.retry.retry_predicate is not None,
                self.retry.custom_wait_func is not None,
            ]
        )
