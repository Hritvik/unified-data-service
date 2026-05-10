"""
Exception utility functions for REST client package.

This module provides utility functions for exception handling,
conversion, and common exception patterns.
"""

from typing import Any, Dict, Optional, Type, Union

import httpx

from .base_exceptions import RestClientBaseException
from .connection_exceptions import (
    ConnectionTimeoutException,
    HostUnreachableException,
    NetworkException,
)
from .request_exceptions import RequestTimeoutException
from .response_exceptions import (
    ResponseTimeoutException,
    UnexpectedResponseException,
)
from .strategy_exceptions import (
    CircuitBreakerOpenException,
)


def convert_httpx_exception(
    exc: Union[httpx.RequestError, httpx.HTTPStatusError],
    context: Optional[Dict[str, Any]] = None,
) -> RestClientBaseException:
    """
    Convert httpx rest_client to appropriate REST client rest_client.

    Args:
        exc: The httpx exception to convert
        context: Additional context information

    Returns:
        Appropriate REST client exception
    """
    context = context or {}

    if isinstance(exc, httpx.ConnectTimeout):
        return ConnectionTimeoutException(
            message=f"Connection timeout: {exc}",
            host=context.get("host"),
            port=context.get("port"),
            timeout_seconds=context.get("timeout"),
            details=context,
            cause=exc,
        )

    elif isinstance(exc, httpx.ReadTimeout):
        return ResponseTimeoutException(
            message=f"Response read timeout: {exc}",
            timeout_seconds=context.get("timeout"),
            timeout_type="read",
            details=context,
            cause=exc,
        )

    elif isinstance(exc, httpx.WriteTimeout):
        return RequestTimeoutException(
            message=f"Request write timeout: {exc}",
            method=context.get("method"),
            url=context.get("url"),
            timeout_seconds=context.get("timeout"),
            timeout_type="write",
            details=context,
            cause=exc,
        )

    elif isinstance(exc, httpx.ConnectError):
        return HostUnreachableException(
            message=f"Host unreachable: {exc}",
            host=context.get("host"),
            port=context.get("port"),
            details=context,
            cause=exc,
        )

    elif isinstance(exc, httpx.HTTPStatusError):
        return UnexpectedResponseException(
            message=f"Unexpected HTTP status: {exc.response.status_code}",
            expected_status_code=context.get("expected_status_code"),
            actual_status_code=exc.response.status_code,
            details=context,
            cause=exc,
        )

    elif isinstance(exc, httpx.TransportError):
        return NetworkException(
            message=f"Transport error: {exc}",
            host=context.get("host"),
            port=context.get("port"),
            details=context,
            cause=exc,
        )

    else:
        # Fallback for unknown httpx rest_client
        return RestClientBaseException(
            message=f"HTTP client error: {exc}",
            details=context,
            cause=exc,
        )


def is_retryable_exception(exc: Exception) -> bool:
    """
    Check if an exception is retryable.

    Args:
        exc: The exception to check

    Returns:
        True if the exception is retryable, False otherwise
    """
    # Network and connection issues are generally retryable
    if isinstance(
        exc, (NetworkException, ConnectionTimeoutException, HostUnreachableException)
    ):
        return True

    # Timeout rest_client are retryable
    if isinstance(exc, (RequestTimeoutException, ResponseTimeoutException)):
        return True

    # httpx rest_client that are retryable
    if isinstance(
        exc,
        (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.ConnectError,
            httpx.TransportError,
        ),
    ):
        return True

    # HTTP status errors that are retryable (5xx server errors)
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600

    return False


def is_circuit_breaker_exception(exc: Exception) -> bool:
    """
    Check if an exception should trigger circuit breaker.

    Args:
        exc: The exception to check

    Returns:
        True if the exception should trigger circuit breaker, False otherwise
    """
    # Circuit breaker rest_client themselves
    if isinstance(exc, CircuitBreakerOpenException):
        return True

    # Network and connection issues should trigger circuit breaker
    if isinstance(exc, (NetworkException, HostUnreachableException)):
        return True

    # httpx connection errors should trigger circuit breaker
    if isinstance(exc, (httpx.ConnectError, httpx.TransportError)):
        return True

    # HTTP status errors that indicate server issues
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600

    return False


def create_exception_with_context(
    exception_class: Type[RestClientBaseException],
    message: str,
    **kwargs: Any,
) -> RestClientBaseException:
    """
    Create an exception with standardized context information.

    Args:
        exception_class: The exception class to instantiate
        message: The error message
        **kwargs: Additional arguments for the exception constructor

    Returns:
        The created exception instance
    """
    # Extract context from kwargs
    context = {}
    for key in [
        "client_identifier",
        "path_identifier",
        "method",
        "url",
        "host",
        "port",
    ]:
        if key in kwargs:
            context[key] = kwargs.pop(key)

    # Add context to details if not already present
    if "details" not in kwargs:
        kwargs["details"] = context
    else:
        kwargs["details"].update(context)

    return exception_class(message, **kwargs)


def format_exception_message(
    base_message: str,
    client_identifier: Optional[str] = None,
    path_identifier: Optional[str] = None,
    method: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    """
    Format an exception message with context information.

    Args:
        base_message: The base error message
        client_identifier: Client identifier
        path_identifier: Path identifier
        method: HTTP method
        url: Request URL

    Returns:
        Formatted error message
    """
    parts = [base_message]

    if client_identifier:
        parts.append(f"client={client_identifier}")

    if path_identifier:
        parts.append(f"path={path_identifier}")

    if method:
        parts.append(f"method={method}")

    if url:
        parts.append(f"url={url}")

    return " | ".join(parts)
