"""
Strategy-related rest_client for REST client package.

This module defines rest_client that are raised when there are issues
with retry strategies, circuit breaker patterns, or other resilience strategies.
"""

from typing import Any, Dict, Optional

from .base_exceptions import RestClientBaseException


class StrategyException(RestClientBaseException):
    """
    Base exception for strategy-related issues.

    This includes problems with retry strategies, circuit breaker patterns,
    and other resilience strategy implementations.
    """

    pass


class CircuitBreakerException(StrategyException):
    """
    Base exception for circuit breaker-related issues.

    This includes circuit breaker configuration problems, state management issues,
    and other circuit breaker-specific problems.
    """

    def __init__(
        self,
        message: str,
        circuit_breaker_name: Optional[str] = None,
        state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the circuit breaker exception.

        Args:
            message: Human-readable error message
            circuit_breaker_name: Name of the circuit breaker
            state: Current state of the circuit breaker
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.circuit_breaker_name = circuit_breaker_name
        self.state = state
        super().__init__(message, details, cause)


class CircuitBreakerOpenException(CircuitBreakerException):
    """
    Exception raised when a circuit breaker is in the OPEN state.

    This indicates that the circuit breaker has detected too many failures
    and is preventing further requests to the failing service.
    """

    def __init__(
        self,
        message: str,
        circuit_breaker_name: str,
        failure_count: Optional[int] = None,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the circuit breaker open exception.

        Args:
            message: Human-readable error message
            circuit_breaker_name: Name of the circuit breaker
            failure_count: Number of failures that caused the circuit to open
            failure_threshold: Threshold at which the circuit opens
            recovery_timeout: Timeout before the circuit can attempt to close
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.failure_count = failure_count
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        super().__init__(message, circuit_breaker_name, "OPEN", details, cause)


class RetryExhaustedException(StrategyException):
    """
    Exception raised when all retry attempts have been exhausted.

    This indicates that a request has been retried the maximum number of times
    and all attempts have failed.
    """

    def __init__(
        self,
        message: str,
        max_attempts: int,
        attempts_made: int,
        last_exception: Optional[Exception] = None,
        retry_strategy: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the retry exhausted exception.

        Args:
            message: Human-readable error message
            max_attempts: Maximum number of retry attempts allowed
            attempts_made: Number of attempts that were actually made
            last_exception: The last exception that occurred
            retry_strategy: Name of the retry strategy used
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.max_attempts = max_attempts
        self.attempts_made = attempts_made
        self.last_exception = last_exception
        self.retry_strategy = retry_strategy
        super().__init__(message, details, cause)
