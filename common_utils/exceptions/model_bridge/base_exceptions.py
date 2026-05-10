"""
Base exception classes for model bridge package.

This module defines the foundational exception hierarchy with base classes
that represent different categories of issues that can occur in the model bridge.
"""

from typing import Any, Dict, Optional


class ModelBridgeBaseException(Exception):
    """
    Base exception class for all model bridge model_bridge.

    This is the root of the exception hierarchy and provides common functionality
    for all model bridge model_bridge.
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


class ModelBridgeConfigurationException(ModelBridgeBaseException):
    """
    Base exception for configuration-related issues.

    Raised when there are problems with model bridge configuration,
    settings, or configuration management.
    """

    pass


class ModelBridgeInvocationException(ModelBridgeBaseException):
    """
    Base exception for invocation-related issues.

    Raised when there are problems with model invocations,
    such as failed requests, timeouts, or invocation context issues.
    """

    pass


class ModelBridgeRegistryException(ModelBridgeBaseException):
    """
    Base exception for registry-related issues.

    Raised when there are problems with model registry operations,
    such as missing models, deployments, or registry connectivity.
    """

    pass


class ModelBridgeStrategyException(ModelBridgeBaseException):
    """
    Base exception for strategy-related issues.

    Raised when there are problems with model bridge strategies,
    such as adapter strategies, routing strategies, or selection strategies.
    """

    pass


class ModelBridgeValidationException(ModelBridgeBaseException):
    """
    Base exception for validation-related issues.

    Raised when data validation fails, such as invalid requests,
    responses, or configuration values.
    """

    pass
