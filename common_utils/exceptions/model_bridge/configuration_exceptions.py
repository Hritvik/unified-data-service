"""
Configuration-related model_bridge for model bridge package.

This module defines model_bridge that are raised when there are issues
with model bridge configuration, settings, or configuration management.
"""

from typing import Any, Dict, Optional

from .base_exceptions import ModelBridgeConfigurationException


class InvalidModelBridgeConfigException(ModelBridgeConfigurationException):
    """
    Exception raised when model bridge configuration is invalid or malformed.

    This includes issues with configuration structure, missing required
    sections, or incompatible configuration values.
    """

    def __init__(
        self,
        message: str,
        config_type: Optional[str] = None,
        config_path: Optional[str] = None,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invalid model bridge config exception.

        Args:
            message: Human-readable error message
            config_type: Type of configuration that is invalid
            config_path: Path to the configuration that is invalid
            field_name: Name of the field that is invalid
            field_value: Value of the field that is invalid
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.config_type = config_type
        self.config_path = config_path
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(message, details, cause)


class MissingModelBridgeConfigException(ModelBridgeConfigurationException):
    """
    Exception raised when required model bridge configuration is missing.

    This includes missing configuration files, missing required fields,
    or missing configuration sources.
    """

    def __init__(
        self,
        message: str,
        missing_item: str,
        item_type: Optional[str] = None,
        config_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the missing model bridge config exception.

        Args:
            message: Human-readable error message
            missing_item: Name of the missing configuration item
            item_type: Type of the missing configuration item
            config_path: Path to the configuration file
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.missing_item = missing_item
        self.item_type = item_type
        self.config_path = config_path
        super().__init__(message, details, cause)


class ModelBridgeConfigValidationException(ModelBridgeConfigurationException):
    """
    Exception raised when model bridge configuration validation fails.

    This includes issues with required fields, invalid values,
    or configuration format problems.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the model bridge config validation exception.

        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            field_value: Value of the field that failed validation
            validation_rule: The validation rule that failed
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule
        super().__init__(message, details, cause)
