"""
Model Bridge Exceptions Module

This module provides a comprehensive exception hierarchy for the model bridge package.
All model_bridge inherit from base classes that represent different types of issues.
"""

from .base_exceptions import (
    ModelBridgeBaseException,
    ModelBridgeConfigurationException,
    ModelBridgeInvocationException,
    ModelBridgeRegistryException,
    ModelBridgeStrategyException,
)
from .configuration_exceptions import (
    InvalidModelBridgeConfigException,
    MissingModelBridgeConfigException,
    ModelBridgeConfigValidationException,
)
from .invocation_exceptions import (
    InvocationContextException,
    InvocationFailedException,
    InvocationTimeoutException,
    ModelInvocationException,
    RoutePlanNotFoundException,
)
from .registry_exceptions import (
    DeploymentNotFoundException,
    ModelNotFoundException,
    RegistryConnectionException,
    RegistryDataException,
)
from .strategy_exceptions import (
    AdapterStrategyException,
    AttributeMatchStrategyException,
    DeploymentSelectionException,
    RequestAdapterException,
    ResponseAdapterException,
    RoutingStrategyException,
    StrategyFactoryException,
)
from .utils import (
    convert_value_error_to_model_bridge_exception,
    create_exception_with_context,
    format_exception_message,
    is_circuit_breaker_exception,
    is_retryable_exception,
)
from .validation_exceptions import (
    InvalidRequestException,
    InvalidResponseException,
    ModelBridgeValidationException,
    UnsupportedAPIContractException,
)

__all__ = [
    # Base model_bridge
    "ModelBridgeBaseException",
    "ModelBridgeConfigurationException",
    "ModelBridgeInvocationException",
    "ModelBridgeRegistryException",
    "ModelBridgeStrategyException",
    "ModelBridgeValidationException",
    # Configuration model_bridge
    "InvalidModelBridgeConfigException",
    "MissingModelBridgeConfigException",
    "ModelBridgeConfigValidationException",
    # Invocation model_bridge
    "InvocationContextException",
    "InvocationFailedException",
    "InvocationTimeoutException",
    "ModelInvocationException",
    "RoutePlanNotFoundException",
    # Registry model_bridge
    "DeploymentNotFoundException",
    "ModelNotFoundException",
    "RegistryConnectionException",
    "RegistryDataException",
    # Strategy model_bridge
    "AdapterStrategyException",
    "AttributeMatchStrategyException",
    "DeploymentSelectionException",
    "RequestAdapterException",
    "ResponseAdapterException",
    "RoutingStrategyException",
    "StrategyFactoryException",
    # Validation model_bridge
    "InvalidRequestException",
    "InvalidResponseException",
    "ModelBridgeValidationException",
    "UnsupportedAPIContractException",
    # Utility functions
    "convert_value_error_to_model_bridge_exception",
    "create_exception_with_context",
    "format_exception_message",
    "is_circuit_breaker_exception",
    "is_retryable_exception",
]
