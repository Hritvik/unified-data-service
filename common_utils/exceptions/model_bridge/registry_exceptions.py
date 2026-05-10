"""
Registry-related model_bridge for model bridge package.

This module defines model_bridge that are raised when there are issues
with model registry operations, missing models, or deployments.
"""

from typing import Any, Dict, Optional

from .base_exceptions import ModelBridgeRegistryException


class ModelNotFoundException(ModelBridgeRegistryException):
    """
    Exception raised when a model is not found in the registry.

    This includes missing models, invalid model names,
    or models that are not accessible.
    """

    def __init__(
        self,
        message: str,
        model_name: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the model not found exception.

        Args:
            message: Human-readable error message
            model_name: Name of the model that was not found
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.model_name = model_name
        super().__init__(message, details, cause)


class DeploymentNotFoundException(ModelBridgeRegistryException):
    """
    Exception raised when a deployment is not found in the registry.

    This includes missing deployments, invalid deployment names,
    or deployments that are not accessible.
    """

    def __init__(
        self,
        message: str,
        deployment_name: str,
        model_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the deployment not found exception.

        Args:
            message: Human-readable error message
            deployment_name: Name of the deployment that was not found
            model_name: Name of the model associated with the deployment
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.deployment_name = deployment_name
        self.model_name = model_name
        super().__init__(message, details, cause)


class RegistryDataException(ModelBridgeRegistryException):
    """
    Exception raised when there are issues with registry data.

    This includes data corruption, invalid data formats,
    or other data-related issues in the registry.
    """

    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        data_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the registry data exception.

        Args:
            message: Human-readable error message
            data_type: Type of data that caused the issue
            data_id: ID of the data that caused the issue
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.data_type = data_type
        self.data_id = data_id
        super().__init__(message, details, cause)


class RegistryConnectionException(ModelBridgeRegistryException):
    """
    Exception raised when there are issues connecting to the registry.

    This includes connection failures, authentication issues,
    or other connectivity problems with the registry.
    """

    def __init__(
        self,
        message: str,
        registry_url: Optional[str] = None,
        connection_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the registry connection exception.

        Args:
            message: Human-readable error message
            registry_url: URL of the registry that failed to connect
            connection_type: Type of connection that failed
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.registry_url = registry_url
        self.connection_type = connection_type
        super().__init__(message, details, cause)
