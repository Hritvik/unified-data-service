"""
REST client native models module.

This module contains native models that encapsulate business logic and serve as
the intermediate layer between document models and API models.
"""

from datetime import timedelta
from typing import Annotated, Any, Callable, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from pydantic import BaseModel, computed_field
from pydantic.json_schema import SkipJsonSchema

from common_utils.enums import CircuitBreakerStrategy, RetryStrategyType


class ConnectionPoolConfigNative(BaseModel):
    """Native model for connection pool configuration with business logic."""

    default_max_per_route: int = 20
    max_total: int = 20

    @computed_field
    def is_default_config(self) -> bool:
        """Check if this is the default configuration."""
        return self.default_max_per_route == 20 and self.max_total == 20

    @computed_field
    def get_total_connections(self) -> int:
        """Get total available connections."""
        return self.max_total

    def validate_configuration(self) -> bool:
        """Validate connection pool configuration."""
        return (
            self.default_max_per_route > 0
            and self.max_total > 0
            and self.default_max_per_route <= self.max_total
        )


class TimeoutConfigNative(BaseModel):
    """Native model for timeout configuration with business logic."""

    connection_timeout: int = 100
    request_timeout: int = 100
    socket_timeout: int = 100
    pool_timeout: int = 100
    read_timeout: int = 100
    write_timeout: int = 100

    @computed_field
    def is_default_config(self) -> bool:
        """Check if this is the default configuration."""
        return all(
            getattr(self, field) == 100
            for field in [
                "connection_timeout",
                "request_timeout",
                "socket_timeout",
                "pool_timeout",
                "read_timeout",
                "write_timeout",
            ]
        )

    @computed_field
    def get_effective_timeout(self) -> int:
        """Get the most restrictive timeout value."""
        return min(
            self.connection_timeout,
            self.request_timeout,
            self.socket_timeout,
            self.pool_timeout,
            self.read_timeout,
            self.write_timeout,
        )

    def to_httpx_timeout(self) -> "httpx.Timeout":
        """Convert to httpx.Timeout object."""
        if httpx is None:
            raise ImportError("httpx is required for httpx.Timeout conversion")
        return httpx.Timeout(
            connect=self.connection_timeout / 1000.0,  # Convert to seconds
            read=self.read_timeout / 1000.0,
            write=self.write_timeout / 1000.0,
            pool=self.pool_timeout / 1000.0,
        )


class CircuitBreakerConfigNative(BaseModel):
    """Native model for circuit breaker configuration with business logic."""

    strategy: CircuitBreakerStrategy = CircuitBreakerStrategy.NONE
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exceptions: List[str] = []
    name: Optional[str] = None
    log_state_changes: bool = True
    log_failures: bool = True

    @computed_field
    def is_enabled(self) -> bool:
        """Check if circuit breaker is enabled."""
        return self.strategy != CircuitBreakerStrategy.NONE

    @computed_field
    def get_effective_strategy(self) -> CircuitBreakerStrategy:
        """Get the effective circuit breaker strategy."""
        return self.strategy

    def should_open_circuit(self, failure_count: int) -> bool:
        """Determine if circuit should open based on failure count."""
        return self.is_enabled and failure_count >= self.failure_threshold

    def get_aiobreaker_config(self) -> Dict[str, Any]:
        """Get aiobreaker-specific configuration."""
        if self.strategy == CircuitBreakerStrategy.AIOBREAKER:
            return {
                "fail_max": self.failure_threshold,
                "timeout_duration": timedelta(seconds=self.recovery_timeout),
                "name": f"circuit_breaker_{id(self)}",
            }
        return {}

    def validate_for_strategy(self) -> bool:
        """Validate configuration for the selected strategy."""
        if self.strategy == CircuitBreakerStrategy.AIOBREAKER:
            return self.failure_threshold > 0 and self.recovery_timeout > 0
        elif self.strategy == CircuitBreakerStrategy.NONE:
            return True
        return False


class RetryConfigNative(BaseModel):
    """Native model for retry configuration with business logic."""

    strategy: RetryStrategyType = RetryStrategyType.NO_RETRY
    max_attempts: int = 3
    wait_seconds: float = 1.0
    multiplier: float = 1.0
    max_interval: float = 10.0
    start_wait: float = 1.0
    increment: float = 1.0
    retryable_exceptions: List[str] = []
    retry_predicate: Annotated[
        Optional[Callable[[Exception], bool]],
        SkipJsonSchema(),
    ] = None
    custom_wait_func: Annotated[
        Optional[Callable[[int], float]],
        SkipJsonSchema(),
    ] = None

    @computed_field
    def is_enabled(self) -> bool:
        """Check if retry is enabled."""
        return self.strategy != RetryStrategyType.NO_RETRY

    @computed_field
    def get_effective_strategy(self) -> RetryStrategyType:
        """Get the effective retry strategy."""
        return self.strategy

    def calculate_wait_time(self, attempt: int) -> float:
        """Calculate wait time for a specific retry attempt."""
        if not self.is_enabled or attempt <= 0:
            return 0.0

        if self.strategy == RetryStrategyType.FIXED_DELAY:
            return self.wait_seconds
        elif self.strategy == RetryStrategyType.EXPONENTIAL_BACKOFF:
            wait_time = self.start_wait * (self.multiplier ** (attempt - 1))
            return min(wait_time, self.max_interval)
        elif self.strategy == RetryStrategyType.LINEAR_BACKOFF:
            wait_time = self.start_wait + (self.increment * (attempt - 1))
            return min(wait_time, self.max_interval)
        else:
            return self.wait_seconds

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if a retry should be attempted."""
        if not self.is_enabled or attempt >= self.max_attempts:
            return False

        # Check if exception is retryable
        exception_name = type(exception).__name__
        return exception_name in self.retryable_exceptions

    def validate_for_strategy(self) -> bool:
        """Validate if the retry configuration is valid for the selected strategy."""
        if self.strategy == RetryStrategyType.NO_RETRY:
            return True

        if self.max_attempts <= 0:
            return False

        if self.strategy in [
            RetryStrategyType.FIXED_DELAY,
            RetryStrategyType.EXPONENTIAL_BACKOFF,
            RetryStrategyType.EXPONENTIAL_BACKOFF_WITH_JITTER,
        ]:
            if self.wait_seconds <= 0 or self.max_interval <= 0:
                return False

        if self.strategy == RetryStrategyType.LINEAR_BACKOFF:
            if self.start_wait <= 0 or self.increment <= 0 or self.max_interval <= 0:
                return False

        if self.strategy == RetryStrategyType.CUSTOM and not self.custom_wait_func:
            return False

        return True


class AuthConfigNative(BaseModel):
    """Native model for authentication configuration with business logic."""

    key: str
    value: str
    type: str = "header"

    @computed_field
    def is_valid(self) -> bool:
        """Check if authentication configuration is valid."""
        return bool(self.key and self.value)

    @computed_field
    def get_header_value(self) -> str:
        """Get the header value for this authentication."""
        if self.type == "header":
            return f"{self.key}: {self.value}"
        return self.value


class CredentialsConfigNative(BaseModel):
    """Native model for credentials configuration with business logic."""

    host: str
    auth: List[AuthConfigNative] = []

    @computed_field
    def is_valid(self) -> bool:
        """Check if credentials configuration is valid."""
        return bool(self.host) and all(auth.is_valid for auth in self.auth)

    @computed_field
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        for auth in self.auth:
            if auth.type == "header" and auth.is_valid:
                headers[auth.key] = auth.value
        return headers

    @computed_field
    def has_authentication(self) -> bool:
        """Check if authentication is configured."""
        return len(self.auth) > 0


class EndpointConfigNative(BaseModel):
    """Native model for endpoint configuration with business logic."""

    path: str
    timeout: Optional[TimeoutConfigNative] = None
    circuit_breaker: Optional[CircuitBreakerConfigNative] = None
    headers: Dict[str, str] = {}
    path_params: Dict[str, str] = {}
    query_params: Dict[str, str] = {}
    retry: Optional[RetryConfigNative] = None
    auth: List[AuthConfigNative] = []

    @computed_field
    def is_valid(self) -> bool:
        """Check if endpoint configuration is valid."""
        return bool(self.path)

    def get_full_path(self, base_url: str = "") -> str:
        """Get the full endpoint path."""
        if base_url:
            return f"{base_url.rstrip('/')}/{self.path.lstrip('/')}"
        return self.path

    @computed_field
    def has_custom_timeout(self) -> bool:
        """Check if endpoint has custom timeout configuration."""
        return self.timeout is not None and not self.timeout.is_default_config

    @computed_field
    def has_custom_circuit_breaker(self) -> bool:
        """Check if endpoint has custom circuit breaker configuration."""
        return self.circuit_breaker is not None and self.circuit_breaker.is_enabled

    @computed_field
    def has_custom_retry(self) -> bool:
        """Check if endpoint has custom retry configuration."""
        return self.retry is not None and self.retry.is_enabled

    def get_effective_headers(self, service_headers: Dict[str, str]) -> Dict[str, str]:
        """Get effective headers combining service and endpoint headers."""
        effective_headers = service_headers.copy()
        effective_headers.update(self.headers)
        return effective_headers


class ServiceConfigNative(BaseModel):
    """Native model for service configuration with business logic."""

    name: str
    activate_at_startup: bool = False
    connection_pool: ConnectionPoolConfigNative
    credentials: Optional[CredentialsConfigNative] = None
    headers: Dict[str, str] = {}
    timeout: TimeoutConfigNative
    circuit_breaker: CircuitBreakerConfigNative
    retry: RetryConfigNative
    endpoints: Dict[str, EndpointConfigNative] = {}

    @computed_field
    def is_fully_configured(self) -> bool:
        """Check if service is fully configured."""
        return (
            bool(self.name)
            and self.connection_pool.validate_configuration()
            and (self.credentials is None or self.credentials.is_valid)
            and self.circuit_breaker.validate_for_strategy()
            and self.retry.validate_for_strategy()
        )

    @computed_field
    def total_endpoints(self) -> int:
        """Get total number of endpoints."""
        return len(self.endpoints)

    @computed_field
    def has_authentication(self) -> bool:
        """Check if service has authentication configured."""
        return self.credentials is not None and self.credentials.has_authentication

    def get_effective_timeout(self, operation: str) -> int:
        """Get effective timeout for a specific operation."""
        timeout_map = {
            "connection": self.timeout.connection_timeout,
            "request": self.timeout.request_timeout,
            "socket": self.timeout.socket_timeout,
            "pool": self.timeout.pool_timeout,
            "read": self.timeout.read_timeout,
            "write": self.timeout.write_timeout,
        }
        return timeout_map.get(operation, self.timeout.request_timeout)

    def get_endpoint_config(self, endpoint_name: str) -> Optional[EndpointConfigNative]:
        """Get endpoint configuration by name."""
        return self.endpoints.get(endpoint_name)

    def validate_endpoint(self, endpoint_name: str) -> bool:
        """Validate if an endpoint is properly configured."""
        endpoint = self.get_endpoint_config(endpoint_name)
        return endpoint is not None and endpoint.is_valid


class RestClientConfigNative(BaseModel):
    """Native model for REST client configuration with business logic."""

    services: Dict[str, ServiceConfigNative] = {}

    @computed_field
    def total_services(self) -> int:
        """Get total number of services."""
        return len(self.services)

    @computed_field
    def total_endpoints(self) -> int:
        """Get total number of endpoints across all services."""
        return sum(service.total_endpoints for service in self.services.values())

    @computed_field
    def active_services(self) -> List[str]:
        """Get list of services that are active at startup."""
        return [
            service_name
            for service_name, service in self.services.items()
            if service.activate_at_startup
        ]

    def get_service_config(self, service_name: str) -> Optional[ServiceConfigNative]:
        """Get service configuration by name."""
        return self.services.get(service_name)

    def get_endpoint_config(
        self, service_name: str, endpoint_name: str
    ) -> Optional[EndpointConfigNative]:
        """Get endpoint configuration by service and endpoint names."""
        service = self.get_service_config(service_name)
        if service:
            return service.get_endpoint_config(endpoint_name)
        return None

    def validate_service(self, service_name: str) -> bool:
        """Validate if a service is properly configured."""
        service = self.get_service_config(service_name)
        return service is not None and service.is_fully_configured

    def get_services_with_authentication(self) -> List[str]:
        """Get list of services that have authentication configured."""
        return [
            service_name
            for service_name, service in self.services.items()
            if service.has_authentication
        ]
