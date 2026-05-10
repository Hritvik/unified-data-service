"""
Base rest_client for consistent error handling across the application.

These rest_client are designed to be caught by the error handling middleware
and formatted according to the BaseResponse model.
"""

from typing import Any, Dict, Optional


class InternalServerException(Exception):
    """Base class for internal server errors (5xx)."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class BadRequestException(Exception):
    """Base class for bad request errors (4xx)."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ProcessingError(InternalServerException):
    """Raised when there's an error processing a request."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, error_code, details)


class InsufficientDataError(BadRequestException):
    """Raised when required data is missing to process a request."""

    def __init__(
        self,
        message: str,
        missing_fields: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.missing_fields = missing_fields or []
        super().__init__(message, "INSUFFICIENT_DATA", details)


class BusinessRuleViolation(BadRequestException):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.rule_name = rule_name
        super().__init__(message, "BUSINESS_RULE_VIOLATION", details)


class DataValidationError(BadRequestException):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.field = field
        self.value = value
        super().__init__(message, "DATA_VALIDATION_ERROR", details)


class ServiceUnavailableError(InternalServerException):
    """Raised when a required service is unavailable."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.service_name = service_name
        super().__init__(message, "SERVICE_UNAVAILABLE", details)


class RateLimitExceededError(BadRequestException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


class AuthenticationError(BadRequestException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.auth_type = auth_type
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(BadRequestException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str,
        required_permissions: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.required_permissions = required_permissions or []
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class ResourceNotFoundError(BadRequestException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, "RESOURCE_NOT_FOUND", details)


class ConflictError(BadRequestException):
    """Raised when there's a conflict with existing data."""

    def __init__(
        self,
        message: str,
        conflict_type: Optional[str] = None,
        conflicting_resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.conflict_type = conflict_type
        self.conflicting_resource = conflicting_resource
        super().__init__(message, "CONFLICT", details)
