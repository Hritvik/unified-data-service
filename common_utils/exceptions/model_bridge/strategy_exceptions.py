"""
Strategy-related model_bridge for model bridge package.

This module defines model_bridge that are raised when there are issues
with model bridge strategies, adapters, and strategy factories.
"""

from typing import Any, Dict, Optional

from .base_exceptions import ModelBridgeStrategyException


class AdapterStrategyException(ModelBridgeStrategyException):
    """
    Base exception for adapter strategy-related issues.

    This includes problems with request adapters, response adapters,
    or other adapter strategy implementations.
    """

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        api_contract: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the adapter strategy exception.

        Args:
            message: Human-readable error message
            strategy_name: Name of the strategy that failed
            api_contract: API contract being processed
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.strategy_name = strategy_name
        self.api_contract = api_contract
        super().__init__(message, details, cause)


class RequestAdapterException(AdapterStrategyException):
    """
    Exception raised when request adapter operations fail.

    This includes request transformation failures, validation errors,
    or other request adapter-specific issues.
    """

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        api_contract: Optional[str] = None,
        request_data: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the request adapter exception.

        Args:
            message: Human-readable error message
            strategy_name: Name of the request adapter strategy
            api_contract: API contract being processed
            request_data: Request data that failed to adapt
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.request_data = request_data
        super().__init__(message, strategy_name, api_contract, details, cause)


class ResponseAdapterException(AdapterStrategyException):
    """
    Exception raised when response adapter operations fail.

    This includes response transformation failures, validation errors,
    or other response adapter-specific issues.
    """

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        api_contract: Optional[str] = None,
        response_data: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the response adapter exception.

        Args:
            message: Human-readable error message
            strategy_name: Name of the response adapter strategy
            api_contract: API contract being processed
            response_data: Response data that failed to adapt
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.response_data = response_data
        super().__init__(message, strategy_name, api_contract, details, cause)


class DeploymentSelectionException(ModelBridgeStrategyException):
    """
    Exception raised when deployment selection strategies fail.

    This includes selection algorithm failures, invalid selection criteria,
    or other deployment selection issues.
    """

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        selection_criteria: Optional[Dict[str, Any]] = None,
        available_deployments: Optional[list[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the deployment selection exception.

        Args:
            message: Human-readable error message
            strategy_name: Name of the selection strategy
            selection_criteria: Criteria used for selection
            available_deployments: List of available deployments
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.strategy_name = strategy_name
        self.selection_criteria = selection_criteria
        self.available_deployments = available_deployments
        super().__init__(message, details, cause)


class RoutingStrategyException(ModelBridgeStrategyException):
    """
    Exception raised when routing strategies fail.

    This includes routing algorithm failures, invalid routing rules,
    or other routing-related issues.
    """

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        routing_rules: Optional[Dict[str, Any]] = None,
        route_plan_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the routing strategy exception.

        Args:
            message: Human-readable error message
            strategy_name: Name of the routing strategy
            routing_rules: Rules used for routing
            route_plan_name: Name of the route plan
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.strategy_name = strategy_name
        self.routing_rules = routing_rules
        self.route_plan_name = route_plan_name
        super().__init__(message, details, cause)


class AttributeMatchStrategyException(ModelBridgeStrategyException):
    """
    Exception raised when attribute match strategies fail.

    This includes attribute matching failures, invalid matching criteria,
    or other attribute matching issues.
    """

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        attribute_name: Optional[str] = None,
        attribute_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the attribute match strategy exception.

        Args:
            message: Human-readable error message
            strategy_name: Name of the attribute match strategy
            attribute_name: Name of the attribute being matched
            attribute_value: Value of the attribute being matched
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.strategy_name = strategy_name
        self.attribute_name = attribute_name
        self.attribute_value = attribute_value
        super().__init__(message, details, cause)


class StrategyFactoryException(ModelBridgeStrategyException):
    """
    Exception raised when strategy factories fail.

    This includes factory creation failures, invalid strategy types,
    or other factory-related issues.
    """

    def __init__(
        self,
        message: str,
        factory_name: Optional[str] = None,
        strategy_type: Optional[str] = None,
        strategy_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the strategy factory exception.

        Args:
            message: Human-readable error message
            factory_name: Name of the factory that failed
            strategy_type: Type of strategy being created
            strategy_name: Name of the strategy being created
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.factory_name = factory_name
        self.strategy_type = strategy_type
        self.strategy_name = strategy_name
        super().__init__(message, details, cause)
