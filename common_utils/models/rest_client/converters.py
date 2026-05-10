"""
REST client converter functions module.

This module provides converter functions for transforming between different model types
following the Response <> Native <> Document pattern. Only the entry-point
``Info → Native`` chain consumed by ``rest_client/config/sources/registry_source.py``
is kept; the legacy ``Document → Native`` and ``Response → Native`` converters
were dropped along with the V1 collections and HTTP-response shapes.
"""

from typing import Dict

from common_utils.models.rest_client.native import (
    AuthConfigNative,
    CircuitBreakerConfigNative,
    ConnectionPoolConfigNative,
    CredentialsConfigNative,
    EndpointConfigNative,
    RestClientConfigNative,
    RetryConfigNative,
    ServiceConfigNative,
    TimeoutConfigNative,
)
from common_utils.models.rest_client_registry.responses import (
    AuthConfigInfo,
    CircuitBreakerConfigInfo,
    ConnectionPoolConfigInfo,
    CredentialsConfigInfo,
    EndpointConfigInfo,
    RetryConfigInfo,
    ServiceConfigInfo,
    ServiceConfigListResponse,
    TimeoutConfigInfo,
)


# Direct Info -> Native converters
def convert_connection_pool_info_to_native(
    info: ConnectionPoolConfigInfo,
) -> ConnectionPoolConfigNative:
    """Convert ConnectionPoolConfigInfo directly to ConnectionPoolConfigNative."""
    return ConnectionPoolConfigNative(
        default_max_per_route=info.default_max_per_route,
        max_total=info.max_total,
    )


def convert_auth_info_to_native(
    info: AuthConfigInfo,
) -> AuthConfigNative:
    """Convert AuthConfigInfo directly to AuthConfigNative."""
    return AuthConfigNative(
        key=info.key,
        value=info.value,
        type="header",  # Default type since it's not in AuthConfigInfo
    )


def convert_credentials_info_to_native(
    info: CredentialsConfigInfo,
) -> CredentialsConfigNative:
    """Convert CredentialsConfigInfo directly to CredentialsConfigNative."""
    return CredentialsConfigNative(
        host=info.host,
        auth=[convert_auth_info_to_native(auth) for auth in info.auth],
    )


def convert_timeout_info_to_native(
    info: TimeoutConfigInfo,
) -> TimeoutConfigNative:
    """Convert TimeoutConfigInfo directly to TimeoutConfigNative."""
    return TimeoutConfigNative(
        connection_timeout=info.connection_timeout,
        request_timeout=info.request_timeout,
        socket_timeout=info.socket_timeout,
        pool_timeout=info.pool_timeout,
        read_timeout=info.read_timeout,
        write_timeout=info.write_timeout,
    )


def convert_circuit_breaker_info_to_native(
    info: CircuitBreakerConfigInfo,
) -> CircuitBreakerConfigNative:
    """Convert CircuitBreakerConfigInfo directly to CircuitBreakerConfigNative."""
    return CircuitBreakerConfigNative(
        strategy=info.strategy,
        failure_threshold=info.failure_threshold,
        recovery_timeout=info.recovery_timeout,
        expected_exceptions=info.expected_exceptions,
    )


def convert_retry_info_to_native(
    info: RetryConfigInfo,
) -> RetryConfigNative:
    """Convert RetryConfigInfo directly to RetryConfigNative."""
    return RetryConfigNative(
        strategy=info.strategy,
        max_attempts=info.max_attempts,
        wait_seconds=info.wait_seconds,
        multiplier=info.multiplier,
        max_interval=info.max_interval,
        start_wait=info.start_wait,
        increment=info.increment,
        retryable_exceptions=info.retryable_exceptions,
    )


def convert_endpoint_info_to_native(
    info: EndpointConfigInfo,
) -> EndpointConfigNative:
    """Convert EndpointConfigInfo directly to EndpointConfigNative."""
    return EndpointConfigNative(
        path=info.path,
        timeout=convert_timeout_info_to_native(info.timeout) if info.timeout else None,
        circuit_breaker=(
            convert_circuit_breaker_info_to_native(info.circuit_breaker)
            if info.circuit_breaker
            else None
        ),
        headers=info.headers,
        path_params=info.path_params,
        query_params=info.query_params,
        retry=convert_retry_info_to_native(info.retry) if info.retry else None,
        auth=[convert_auth_info_to_native(auth) for auth in info.auth],
    )


def convert_service_info_to_native(
    info: ServiceConfigInfo,
) -> ServiceConfigNative:
    """Convert ServiceConfigInfo directly to ServiceConfigNative."""
    return ServiceConfigNative(
        name=info.name,
        activate_at_startup=info.activate_at_startup,
        connection_pool=convert_connection_pool_info_to_native(info.connection_pool),
        credentials=(
            convert_credentials_info_to_native(info.credentials)
            if info.credentials
            else None
        ),
        headers=info.headers,
        timeout=convert_timeout_info_to_native(info.timeout),
        circuit_breaker=convert_circuit_breaker_info_to_native(info.circuit_breaker),
        retry=convert_retry_info_to_native(info.retry),
        endpoints={},  # Endpoints are stitched in by the caller post-conversion.
    )


def convert_service_list_response_to_native(
    api_model: ServiceConfigListResponse,
) -> Dict[str, ServiceConfigNative]:
    """Convert ServiceConfigListResponse to dict of ServiceConfigNative."""
    return {
        service_response.name: convert_service_info_to_native(service_response)
        for service_response in api_model.data
    }


def convert_service_list_response_to_rest_client_native(
    api_model: ServiceConfigListResponse,
) -> RestClientConfigNative:
    """Convert ServiceConfigListResponse to RestClientConfigNative."""
    services = convert_service_list_response_to_native(api_model)

    return RestClientConfigNative(services=services)
