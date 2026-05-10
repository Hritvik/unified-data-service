"""
Base exception classes for REST client package.

This module defines the foundational exception hierarchy with base classes
that represent different categories of issues that can occur in the REST client.
"""

from typing import Any, Dict, Optional


class RestClientBaseException(Exception):
    """
    Base exception class for all REST client rest_client.

    This is the root of the exception hierarchy and provides common functionality
    for all REST client rest_client.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the base exception.

        Args:
            message: Human-readable error message
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.message = message
        self.details = details or {}
        self.cause = cause

        # Build the full message
        full_message = message
        if details:
            details_str = ", ".join(f"{k}={v}" for k, v in details.items())
            full_message = f"{message} - Details: {details_str}"

        super().__init__(full_message)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return self.message

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        return f"{self.__class__.__name__}(message='{self.message}', details={self.details})"


class RestClientConfigurationException(RestClientBaseException):
    """
    Base exception for configuration-related issues.

    Raised when there are problems with client configuration, settings,
    or configuration sources.
    """

    pass


class RestClientConnectionException(RestClientBaseException):
    """
    Base exception for connection-related issues.

    Raised when there are problems establishing or maintaining connections
    to remote services.
    """

    pass


class RestClientRequestException(RestClientBaseException):
    """
    Base exception for request-related issues.

    Raised when there are problems with outgoing HTTP requests,
    such as invalid parameters, unsupported methods, or request timeouts.
    """

    pass


class RestClientResponseException(RestClientBaseException):
    """
    Base exception for response-related issues.

    Raised when there are problems with incoming HTTP responses,
    such as invalid responses, unexpected status codes, or response timeouts.
    """

    pass


class RestClientTimeoutException(RestClientBaseException):
    """
    Base exception for timeout-related issues.

    Raised when operations exceed their configured timeouts,
    including connection timeouts, request timeouts, and response timeouts.
    """

    pass


class RestClientValidationException(RestClientBaseException):
    """
    Base exception for validation-related issues.

    Raised when data validation fails, such as invalid request parameters,
    response data, or configuration values.
    """

    pass
