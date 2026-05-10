"""
Validation rest_client for REST client operations.
"""

from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Base class for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


class ConfigurationValidationError(ValidationError):
    """Raised when configuration validation fails."""

    def __init__(
        self, message: str, config_path: Optional[str] = None, config_value: Any = None
    ):
        super().__init__(message, config_path, config_value)
        self.config_path = config_path
        self.config_value = config_value


class RequestValidationError(ValidationError):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        request_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, field, value)
        self.request_data = request_data or {}


class ResponseValidationError(ValidationError):
    """Raised when response validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message, field, value)
        self.response_data = response_data or {}
        self.status_code = status_code


class URLValidationError(ValidationError):
    """Raised when URL validation fails."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        path_params: Optional[Dict[str, str]] = None,
    ):
        super().__init__(message, "url", url)
        self.url = url
        self.path_params = path_params or {}


class HeaderValidationError(ValidationError):
    """Raised when header validation fails."""

    def __init__(
        self,
        message: str,
        header_name: Optional[str] = None,
        header_value: Optional[str] = None,
    ):
        super().__init__(message, header_name, header_value)
        self.header_name = header_name
        self.header_value = header_value


class TimeoutValidationError(ValidationError):
    """Raised when timeout configuration is invalid."""

    def __init__(self, message: str, timeout_config: Optional[Dict[str, Any]] = None):
        super().__init__(message, "timeout", timeout_config)
        self.timeout_config = timeout_config or {}


class RetryValidationError(ValidationError):
    """Raised when retry configuration is invalid."""

    def __init__(self, message: str, retry_config: Optional[Dict[str, Any]] = None):
        super().__init__(message, "retry", retry_config)
        self.retry_config = retry_config or {}


class CircuitBreakerValidationError(ValidationError):
    """Raised when circuit breaker configuration is invalid."""

    def __init__(
        self, message: str, circuit_breaker_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "circuit_breaker", circuit_breaker_config)
        self.circuit_breaker_config = circuit_breaker_config or {}


class ValidationErrorCollection(Exception):
    """Collection of multiple validation errors."""

    def __init__(self, errors: List[ValidationError]) -> None:
        self.errors = errors
        message = f"Multiple validation errors occurred: {len(errors)} errors"
        super().__init__(message)

    def __str__(self) -> str:
        error_messages = []
        for i, error in enumerate(self.errors, 1):
            error_messages.append(f"{i}. {error.message}")
            if error.field:
                error_messages.append(f"   Field: {error.field}")
            if error.value is not None:
                error_messages.append(f"   Value: {error.value}")
        return "\n".join(error_messages)
