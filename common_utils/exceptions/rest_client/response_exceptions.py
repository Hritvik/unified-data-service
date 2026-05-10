"""
Response-related rest_client for REST client package.

This module defines rest_client that are raised when there are issues
with incoming HTTP responses, response processing, or response validation.
"""

from typing import Any, Dict, Optional

from .base_exceptions import RestClientResponseException, RestClientTimeoutException


class InvalidResponseException(RestClientResponseException):
    """
    Exception raised when a response is invalid or malformed.

    This includes issues with response format, content type,
    or other response structure problems.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        content_type: Optional[str] = None,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invalid response exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code of the invalid response
            content_type: Content type of the invalid response
            field_name: Name of the field that was invalid
            field_value: Value of the field that was invalid
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.status_code = status_code
        self.content_type = content_type
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(message, details, cause)


class UnexpectedResponseException(RestClientResponseException):
    """
    Exception raised when a response is unexpected.

    This includes unexpected status codes, unexpected content types,
    or other unexpected response characteristics.
    """

    def __init__(
        self,
        message: str,
        expected_status_code: Optional[int] = None,
        actual_status_code: Optional[int] = None,
        expected_content_type: Optional[str] = None,
        actual_content_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the unexpected response exception.

        Args:
            message: Human-readable error message
            expected_status_code: Expected HTTP status code
            actual_status_code: Actual HTTP status code received
            expected_content_type: Expected content type
            actual_content_type: Actual content type received
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.expected_status_code = expected_status_code
        self.actual_status_code = actual_status_code
        self.expected_content_type = expected_content_type
        self.actual_content_type = actual_content_type
        super().__init__(message, details, cause)


class ResponseTimeoutException(RestClientTimeoutException):
    """
    Exception raised when a response times out.

    This includes response read timeouts, response processing timeouts,
    and other response-level timeout issues.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        timeout_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the response timeout exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code of the timed out response
            timeout_seconds: Timeout duration in seconds
            timeout_type: Type of timeout (read, processing, etc.)
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.status_code = status_code
        self.timeout_seconds = timeout_seconds
        self.timeout_type = timeout_type
        super().__init__(message, details, cause)
