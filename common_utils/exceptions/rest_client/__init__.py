"""
REST Client Exceptions Module

This module provides a comprehensive exception hierarchy for the REST client package.
All rest_client inherit from base classes that represent different types of issues.
"""

from .base_exceptions import (
    RestClientBaseException,
    RestClientConfigurationException,
    RestClientConnectionException,
    RestClientRequestException,
    RestClientResponseException,
    RestClientTimeoutException,
    RestClientValidationException,
)
from .configuration_exceptions import (
    ConfigSourceException,
    ConfigValidationException,
    InvalidConfigException,
    MissingConfigException,
)
from .connection_exceptions import (
    ConnectionPoolException,
    ConnectionTimeoutException,
    HostUnreachableException,
    NetworkException,
)
from .request_exceptions import (
    InvalidRequestException,
    RequestTimeoutException,
    UnsupportedMethodException,
)
from .response_exceptions import (
    InvalidResponseException,
    ResponseTimeoutException,
    UnexpectedResponseException,
)
from .strategy_exceptions import (
    CircuitBreakerException,
    CircuitBreakerOpenException,
    RetryExhaustedException,
    StrategyException,
)
from .utils import (
    convert_httpx_exception,
    create_exception_with_context,
    format_exception_message,
    is_circuit_breaker_exception,
    is_retryable_exception,
)

__all__ = [
    # Base rest_client
    "RestClientBaseException",
    "RestClientConfigurationException",
    "RestClientConnectionException",
    "RestClientRequestException",
    "RestClientResponseException",
    "RestClientTimeoutException",
    "RestClientValidationException",
    # Configuration rest_client
    "ConfigSourceException",
    "ConfigValidationException",
    "InvalidConfigException",
    "MissingConfigException",
    # Connection rest_client
    "ConnectionPoolException",
    "ConnectionTimeoutException",
    "HostUnreachableException",
    "NetworkException",
    # Request rest_client
    "InvalidRequestException",
    "RequestTimeoutException",
    "UnsupportedMethodException",
    # Response rest_client
    "InvalidResponseException",
    "ResponseTimeoutException",
    "UnexpectedResponseException",
    # Strategy rest_client
    "CircuitBreakerException",
    "CircuitBreakerOpenException",
    "RetryExhaustedException",
    "StrategyException",
    # Utility functions
    "convert_httpx_exception",
    "create_exception_with_context",
    "format_exception_message",
    "is_circuit_breaker_exception",
    "is_retryable_exception",
]
