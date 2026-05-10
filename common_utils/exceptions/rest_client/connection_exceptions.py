"""
Connection-related rest_client for REST client package.

This module defines rest_client that are raised when there are issues
with network connections, connection pools, or connectivity.
"""

from typing import Any, Dict, Optional

from .base_exceptions import RestClientConnectionException


class NetworkException(RestClientConnectionException):
    """
    Base exception for network-related issues.

    This includes general network problems, DNS resolution failures,
    and other network-level issues.
    """

    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the network exception.

        Args:
            message: Human-readable error message
            host: Host that could not be reached
            port: Port that could not be reached
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.host = host
        self.port = port
        super().__init__(message, details, cause)


class HostUnreachableException(NetworkException):
    """
    Exception raised when a host cannot be reached.

    This includes DNS resolution failures, network unreachability,
    and other host-level connectivity issues.
    """

    def __init__(
        self,
        message: str,
        host: str,
        port: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the host unreachable exception.

        Args:
            message: Human-readable error message
            host: Host that could not be reached
            port: Port that could not be reached
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        super().__init__(message, host, port, details, cause)


class ConnectionTimeoutException(RestClientConnectionException):
    """
    Exception raised when connection establishment times out.

    This includes connection timeouts, SSL handshake timeouts,
    and other connection establishment issues.
    """

    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the connection timeout exception.

        Args:
            message: Human-readable error message
            host: Host that timed out
            port: Port that timed out
            timeout_seconds: Timeout duration in seconds
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        super().__init__(message, details, cause)


class ConnectionPoolException(RestClientConnectionException):
    """
    Exception raised when there are issues with connection pools.

    This includes pool exhaustion, pool configuration issues,
    and other connection pool management problems.
    """

    def __init__(
        self,
        message: str,
        pool_name: Optional[str] = None,
        pool_size: Optional[int] = None,
        available_connections: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize the connection pool exception.

        Args:
            message: Human-readable error message
            pool_name: Name of the connection pool
            pool_size: Total size of the connection pool
            available_connections: Number of available connections
            details: Additional error details for debugging
            cause: The original exception that caused this one
        """
        self.pool_name = pool_name
        self.pool_size = pool_size
        self.available_connections = available_connections
        super().__init__(message, details, cause)
