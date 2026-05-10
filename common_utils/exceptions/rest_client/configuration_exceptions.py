"""
Configuration-related rest_client for REST client package.

This module defines rest_client that are raised when there are issues
with configuration loading, validation, or management.
"""

from typing import Any, Dict, Optional

from .base_exceptions import RestClientConfigurationException


class ConfigSourceException(RestClientConfigurationException):
    """
    Exception raised when there are issues with configuration sources.

    This includes problems with YAML files, MongoDB connections,
    registry services, or any other configuration source.
    """

    def __init__(
        self,
        message: str,
        source_name: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the configuration source exception.

        Args:
            message: Human-readable error message
            source_name: Name of the configuration source that failed
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.source_name = source_name
        super().__init__(message, details, cause)


class ConfigValidationException(RestClientConfigurationException):
    """
    Exception raised when configuration validation fails.

    This includes issues with required fields, invalid values,
    or configuration format problems.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the configuration validation exception.

        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            field_value: Value of the field that failed validation
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(message, details, cause)


class InvalidConfigException(RestClientConfigurationException):
    """
    Exception raised when configuration is invalid or malformed.

    This includes issues with configuration structure, missing required
    sections, or incompatible configuration values.
    """

    def __init__(
        self,
        message: str,
        config_type: Optional[str] = None,
        config_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invalid configuration exception.

        Args:
            message: Human-readable error message
            config_type: Type of configuration that is invalid
            config_path: Path to the configuration that is invalid
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.config_type = config_type
        self.config_path = config_path
        super().__init__(message, details, cause)


class MissingConfigException(RestClientConfigurationException):
    """
    Exception raised when required configuration is missing.

    This includes missing configuration files, missing required fields,
    or missing configuration sources.
    """

    def __init__(
        self,
        message: str,
        missing_item: str,
        item_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the missing configuration exception.

        Args:
            message: Human-readable error message
            missing_item: Name of the missing configuration item
            item_type: Type of the missing configuration item
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.missing_item = missing_item
        self.item_type = item_type
        super().__init__(message, details, cause)
