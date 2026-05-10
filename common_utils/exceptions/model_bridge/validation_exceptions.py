"""
Validation-related model_bridge for model bridge package.

This module defines model_bridge that are raised when there are issues
with data validation, API contracts, and request/response validation.
"""

from typing import Any, Dict, Optional

from .base_exceptions import ModelBridgeValidationException


class InvalidRequestException(ModelBridgeValidationException):
    """
    Exception raised when a request is invalid or malformed.

    This includes issues with request format, missing required fields,
    or other request validation problems.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        request_data: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invalid request exception.

        Args:
            message: Human-readable error message
            field_name: Name of the field that is invalid
            field_value: Value of the field that is invalid
            request_data: The request data that failed validation
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.field_name = field_name
        self.field_value = field_value
        self.request_data = request_data
        super().__init__(message, details, cause)


class InvalidResponseException(ModelBridgeValidationException):
    """
    Exception raised when a response is invalid or malformed.

    This includes issues with response format, missing required fields,
    or other response validation problems.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        response_data: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invalid response exception.

        Args:
            message: Human-readable error message
            field_name: Name of the field that is invalid
            field_value: Value of the field that is invalid
            response_data: The response data that failed validation
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.field_name = field_name
        self.field_value = field_value
        self.response_data = response_data
        super().__init__(message, details, cause)


class UnsupportedAPIContractException(ModelBridgeValidationException):
    """
    Exception raised when an API contract is not supported.

    This includes unsupported contract types, missing contract implementations,
    or other API contract-related issues.
    """

    def __init__(
        self,
        message: str,
        api_contract: str,
        supported_contracts: Optional[list[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the unsupported API contract exception.

        Args:
            message: Human-readable error message
            api_contract: The API contract that is not supported
            supported_contracts: List of supported API contracts
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.api_contract = api_contract
        self.supported_contracts = supported_contracts or []
        super().__init__(message, details, cause)
