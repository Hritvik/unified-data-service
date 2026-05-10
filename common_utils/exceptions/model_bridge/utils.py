"""
Exception utility functions for model bridge package.

This module provides utility functions for exception handling,
conversion, and common exception patterns.
"""

from typing import Any, Dict, Optional, Type

from .base_exceptions import ModelBridgeBaseException
from .invocation_exceptions import (
    InvocationContextException,
    InvocationFailedException,
    ModelInvocationException,
    RoutePlanNotFoundException,
)
from .registry_exceptions import (
    DeploymentNotFoundException,
    ModelNotFoundException,
    RegistryConnectionException,
)
from .strategy_exceptions import (
    RequestAdapterException,
    ResponseAdapterException,
    StrategyFactoryException,
)
from .validation_exceptions import (
    InvalidRequestException,
    InvalidResponseException,
    UnsupportedAPIContractException,
)


def create_exception_with_context(
    exception_class: Type[ModelBridgeBaseException],
    message: str,
    **kwargs: Any,
) -> ModelBridgeBaseException:
    """
    Create an exception with standardized context information.

    Args:
        exception_class: The exception class to instantiate
        message: The error message
        **kwargs: Additional arguments for the exception constructor

    Returns:
        The created exception instance
    """
    # Extract context from kwargs
    context = {}
    for key in [
        "invocation_id",
        "route_plan_name",
        "model_name",
        "deployment_name",
        "strategy_name",
        "api_contract",
        "field_name",
    ]:
        if key in kwargs:
            context[key] = kwargs.pop(key)

    # Add context to details if not already present
    if "details" not in kwargs:
        kwargs["details"] = context
    else:
        kwargs["details"].update(context)

    return exception_class(message, **kwargs)


def format_exception_message(
    base_message: str,
    invocation_id: Optional[str] = None,
    route_plan_name: Optional[str] = None,
    model_name: Optional[str] = None,
    deployment_name: Optional[str] = None,
    strategy_name: Optional[str] = None,
    api_contract: Optional[str] = None,
) -> str:
    """
    Format an exception message with context information.

    Args:
        base_message: The base error message
        invocation_id: Invocation ID
        route_plan_name: Route plan name
        model_name: Model name
        deployment_name: Deployment name
        strategy_name: Strategy name
        api_contract: API contract

    Returns:
        Formatted error message
    """
    parts = [base_message]

    if invocation_id:
        parts.append(f"invocation_id={invocation_id}")

    if route_plan_name:
        parts.append(f"route_plan={route_plan_name}")

    if model_name:
        parts.append(f"model={model_name}")

    if deployment_name:
        parts.append(f"deployment={deployment_name}")

    if strategy_name:
        parts.append(f"strategy={strategy_name}")

    if api_contract:
        parts.append(f"api_contract={api_contract}")

    return " | ".join(parts)


def is_retryable_exception(exc: Exception) -> bool:
    """
    Check if an exception is retryable.

    Args:
        exc: The exception to check

    Returns:
        True if the exception is retryable, False otherwise
    """
    # Import REST client model_bridge for checking
    try:
        from common_utils.exceptions.rest_client import (
            CircuitBreakerOpenException,
            RestClientConnectionException,
            RestClientTimeoutException,
            RetryExhaustedException,
        )

        # REST client model_bridge that are retryable
        if isinstance(exc, RestClientConnectionException):
            return True
        if isinstance(exc, RestClientTimeoutException):
            return True
        if isinstance(exc, RetryExhaustedException):
            return False  # Already exhausted retries
        if isinstance(exc, CircuitBreakerOpenException):
            return False  # Circuit breaker is open
    except ImportError:
        pass  # REST client model_bridge not available

    # Registry connection issues are generally retryable
    if isinstance(exc, RegistryConnectionException):
        return True

    # Model invocation model_bridge might be retryable depending on the cause
    if isinstance(exc, ModelInvocationException):
        # Check if the cause is retryable
        if exc.cause:
            return is_retryable_exception(exc.cause)
        return False

    # Invocation context model_bridge are generally not retryable
    if isinstance(exc, InvocationContextException):
        return False

    # Strategy model_bridge are generally not retryable
    if isinstance(
        exc,
        (RequestAdapterException, ResponseAdapterException, StrategyFactoryException),
    ):
        return False

    # Validation model_bridge are generally not retryable
    if isinstance(
        exc,
        (
            InvalidRequestException,
            InvalidResponseException,
            UnsupportedAPIContractException,
        ),
    ):
        return False

    # Not found model_bridge are generally not retryable
    if isinstance(
        exc,
        (
            RoutePlanNotFoundException,
            ModelNotFoundException,
            DeploymentNotFoundException,
        ),
    ):
        return False

    return False


def is_circuit_breaker_exception(exc: Exception) -> bool:
    """
    Check if an exception should trigger circuit breaker.

    Args:
        exc: The exception to check

    Returns:
        True if the exception should trigger circuit breaker, False otherwise
    """
    # Import REST client model_bridge for checking
    try:
        from common_utils.exceptions.rest_client import (
            CircuitBreakerException,
            CircuitBreakerOpenException,
            RestClientConnectionException,
            RestClientTimeoutException,
        )

        # REST client model_bridge that should trigger circuit breaker
        if isinstance(exc, RestClientConnectionException):
            return True
        if isinstance(exc, RestClientTimeoutException):
            return True
        if isinstance(exc, CircuitBreakerException):
            return True
        if isinstance(exc, CircuitBreakerOpenException):
            return True
    except ImportError:
        pass  # REST client model_bridge not available

    # Registry connection issues should trigger circuit breaker
    if isinstance(exc, RegistryConnectionException):
        return True

    # Model invocation model_bridge should trigger circuit breaker
    if isinstance(exc, ModelInvocationException):
        return True

    # Invocation failed model_bridge should trigger circuit breaker
    if isinstance(exc, InvocationFailedException):
        return True

    # Strategy model_bridge generally should not trigger circuit breaker
    if isinstance(
        exc,
        (RequestAdapterException, ResponseAdapterException, StrategyFactoryException),
    ):
        return False

    # Validation model_bridge should not trigger circuit breaker
    if isinstance(
        exc,
        (
            InvalidRequestException,
            InvalidResponseException,
            UnsupportedAPIContractException,
        ),
    ):
        return False

    # Not found model_bridge should not trigger circuit breaker
    if isinstance(
        exc,
        (
            RoutePlanNotFoundException,
            ModelNotFoundException,
            DeploymentNotFoundException,
        ),
    ):
        return False

    return False


def convert_value_error_to_model_bridge_exception(
    exc: ValueError,
    context: Optional[Dict[str, Any]] = None,
) -> ModelBridgeBaseException:
    """
    Convert ValueError model_bridge to appropriate model bridge model_bridge.

    Args:
        exc: The ValueError to convert
        context: Additional context information

    Returns:
        Appropriate model bridge exception
    """
    context = context or {}
    message = str(exc)

    # Check for specific error patterns
    if "Route plan" in message and "not found" in message:
        # Extract route plan name from message
        import re

        match = re.search(r"Route plan ([^\s]+) not found", message)
        route_plan_name = match.group(1) if match else "unknown"
        return RoutePlanNotFoundException(
            message=message,
            route_plan_name=route_plan_name,
            details=context,
            cause=exc,
        )

    elif "Model" in message and "not found" in message:
        # Extract model name from message
        import re

        match = re.search(r"Model ([^\s]+) not found", message)
        model_name = match.group(1) if match else "unknown"
        return ModelNotFoundException(
            message=message,
            model_name=model_name,
            details=context,
            cause=exc,
        )

    elif "Deployment" in message and "not found" in message:
        # Extract deployment name from message
        import re

        match = re.search(r"Deployment ([^\s]+) not found", message)
        deployment_name = match.group(1) if match else "unknown"
        return DeploymentNotFoundException(
            message=message,
            deployment_name=deployment_name,
            details=context,
            cause=exc,
        )

    elif "API contract" in message and "not supported" in message:
        # Extract API contract from message
        import re

        match = re.search(r"API contract ([^\s]+) not supported", message)
        api_contract = match.group(1) if match else "unknown"
        return UnsupportedAPIContractException(
            message=message,
            api_contract=api_contract,
            details=context,
            cause=exc,
        )

    elif "Invocation context" in message and "not found" in message:
        # Extract invocation ID from message
        import re

        match = re.search(r"Invocation context with ID ([^\s]+) not found", message)
        invocation_id = match.group(1) if match else "unknown"
        return InvocationContextException(
            message=message,
            invocation_id=invocation_id,
            details=context,
            cause=exc,
        )

    else:
        # Fallback to validation exception
        return InvalidRequestException(
            message=message,
            details=context,
            cause=exc,
        )
