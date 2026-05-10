"""
Invocation-related model_bridge for model bridge package.

This module defines model_bridge that are raised when there are issues
with model invocations, route plans, and invocation context.
"""

from typing import Any, Dict, Optional

from .base_exceptions import ModelBridgeInvocationException


class RoutePlanNotFoundException(ModelBridgeInvocationException):
    """
    Exception raised when a route plan is not found.

    This includes missing route plans, invalid route plan names,
    or route plans that are not accessible.
    """

    def __init__(
        self,
        message: str,
        route_plan_name: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the route plan not found exception.

        Args:
            message: Human-readable error message
            route_plan_name: Name of the route plan that was not found
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.route_plan_name = route_plan_name
        super().__init__(message, details, cause)


class RoutePlanExecutionException(ModelBridgeInvocationException):
    """
    Exception raised when a route plan execution fails.

    This includes route plan execution errors, invalid route plan names,
    or route plans that are not accessible.

    This is a catch-all exception for route plan execution failures.
    """

    def __init__(
        self,
        message: str,
        route_plan_name: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the route plan execution exception.
        """
        self.route_plan_name = route_plan_name
        super().__init__(message, details, cause)


class ModelInvocationException(ModelBridgeInvocationException):
    """
    Exception raised when model invocation fails.

    This includes model execution errors, provider errors,
    or other model-specific invocation issues.
    """

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        deployment_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the model invocation exception.

        Args:
            message: Human-readable error message
            model_name: Name of the model that failed
            deployment_name: Name of the deployment that failed
            provider_name: Name of the provider that failed
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.model_name = model_name
        self.deployment_name = deployment_name
        self.provider_name = provider_name
        super().__init__(message, details, cause)


class InvocationFailedException(ModelBridgeInvocationException):
    """
    Exception raised when an invocation fails after all attempts.

    This includes failed invocations after retries, exhausted attempts,
    or other invocation failure scenarios.
    """

    def __init__(
        self,
        message: str,
        invocation_id: Optional[str] = None,
        attempt_count: Optional[int] = None,
        max_attempts: Optional[int] = None,
        failure_reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invocation failed exception.

        Args:
            message: Human-readable error message
            invocation_id: ID of the failed invocation
            attempt_count: Number of attempts made
            max_attempts: Maximum number of attempts allowed
            failure_reason: Reason for the failure
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.invocation_id = invocation_id
        self.attempt_count = attempt_count
        self.max_attempts = max_attempts
        self.failure_reason = failure_reason
        super().__init__(message, details, cause)


class InvocationTimeoutException(ModelBridgeInvocationException):
    """
    Exception raised when an invocation times out.

    This includes request timeouts, response timeouts,
    or other timeout-related issues during invocation.
    """

    def __init__(
        self,
        message: str,
        invocation_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        timeout_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invocation timeout exception.

        Args:
            message: Human-readable error message
            invocation_id: ID of the timed out invocation
            timeout_seconds: Timeout duration in seconds
            timeout_type: Type of timeout (request, response, etc.)
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.invocation_id = invocation_id
        self.timeout_seconds = timeout_seconds
        self.timeout_type = timeout_type
        super().__init__(message, details, cause)


class InvocationContextException(ModelBridgeInvocationException):
    """
    Exception raised when there are issues with invocation context.

    This includes context creation failures, context updates,
    or other context-related issues.
    """

    def __init__(
        self,
        message: str,
        invocation_id: Optional[str] = None,
        context_operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the invocation context exception.

        Args:
            message: Human-readable error message
            invocation_id: ID of the invocation context
            context_operation: Operation that failed on the context
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.invocation_id = invocation_id
        self.context_operation = context_operation
        super().__init__(message, details, cause)


class ProviderErrorException(ModelBridgeInvocationException):
    """
    Exception raised when a provider returns an error response.

    This exception captures provider-specific error information
    and provides context about what exactly failed during the
    provider invocation.
    """

    def __init__(
        self,
        message: str,
        provider_name: str,
        api_contract: str,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        deployment_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the provider error exception.

        Args:
            message: Human-readable error message
            provider_name: Name of the provider that returned the error
            api_contract: The API contract being used
            error_code: Provider-specific error code
            error_type: Provider-specific error type
            error_details: Additional provider error details
            model_name: Name of the model that was being invoked
            deployment_name: Name of the deployment that was being used
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.provider_name = provider_name
        self.api_contract = api_contract
        self.error_code = error_code
        self.error_type = error_type
        self.error_details = error_details or {}
        self.model_name = model_name
        self.deployment_name = deployment_name

        # Merge provider error details with general details
        merged_details = details or {}
        if error_details:
            merged_details["provider_error_details"] = error_details
        if error_code:
            merged_details["provider_error_code"] = error_code
        if error_type:
            merged_details["provider_error_type"] = error_type

        super().__init__(message, merged_details, cause)

    def get_failure_reason(self) -> str:
        """
        Get a standardized failure reason for the add_failed_attempt call.

        Returns:
            A string describing what exactly failed
        """
        if self.error_type:
            return f"provider_error_{self.error_type.lower()}"
        elif self.error_code:
            return f"provider_error_{self.error_code.lower()}"
        else:
            return "provider_error_unknown"
