"""
Request-related rest_client for REST client package.

This module defines rest_client that are raised when there are issues
with outgoing HTTP requests, request parameters, or request processing.
"""

from typing import Any, Dict, Optional

from .base_exceptions import RestClientRequestException, RestClientTimeoutException


class InvalidRequestException(RestClientRequestException):
    """
    Exception raised when a request is invalid or malformed.

    This includes issues with request parameters, headers, body,
    or other request components.
    """

    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        url: Optional[str] = None,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invalid request exception.

        Args:
            message: Human-readable error message
            method: HTTP method that was invalid
            url: URL that was invalid
            field_name: Name of the field that was invalid
            field_value: Value of the field that was invalid
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.method = method
        self.url = url
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(message, details, cause)


class UnsupportedMethodException(RestClientRequestException):
    """
    Exception raised when an HTTP method is not supported.

    This includes unsupported HTTP methods or methods that are
    not allowed for a particular endpoint.
    """

    def __init__(
        self,
        message: str,
        method: str,
        supported_methods: Optional[list[str]] = None,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the unsupported method exception.

        Args:
            message: Human-readable error message
            method: HTTP method that is not supported
            supported_methods: List of supported HTTP methods
            url: URL for which the method is not supported
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.method = method
        self.supported_methods = supported_methods or []
        self.url = url
        super().__init__(message, details, cause)


class RequestTimeoutException(RestClientTimeoutException):
    """
    Exception raised when a request times out.

    This includes request timeouts, read timeouts, write timeouts,
    and other request-level timeout issues.
    """

    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        timeout_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the request timeout exception.

        Args:
            message: Human-readable error message
            method: HTTP method that timed out
            url: URL that timed out
            timeout_seconds: Timeout duration in seconds
            timeout_type: Type of timeout (read, write, request, etc.)
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.method = method
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.timeout_type = timeout_type
        super().__init__(message, details, cause)
