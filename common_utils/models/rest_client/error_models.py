"""
Error handling models for REST client package.

This module provides models for error context and result handling
in the REST client system.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from common_utils.enums import ErrorCategory


@dataclass
class ErrorContext:
    """Context information for REST client errors."""

    error_category: ErrorCategory
    error_type: str
    is_retryable: bool
    retry_count: int = 0
    max_retries: int = 0
    circuit_breaker_state: Optional[str] = None
    downstream_status_code: Optional[int] = None
    timeout_seconds: Optional[float] = None
    network_details: Optional[Dict[str, Any]] = None
    configuration_details: Optional[Dict[str, Any]] = None
    request_details: Optional[Dict[str, Any]] = None
    response_details: Optional[Dict[str, Any]] = None


@dataclass
class RestClientResult:
    """Result of a REST client operation."""

    success: bool
    data: Optional[Any] = None
    error: Optional[Exception] = None
    error_context: Optional[ErrorContext] = None
    retry_count: int = 0
    duration_ms: float = 0.0
    status_code: Optional[int] = None
    headers: Optional[Dict[str, str]] = None

    @classmethod
    def success_result(
        cls,
        data: Any,
        duration_ms: float = 0.0,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> "RestClientResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            duration_ms=duration_ms,
            status_code=status_code,
            headers=headers,
        )

    @classmethod
    def error_result(
        cls,
        error: Exception,
        error_context: ErrorContext,
        duration_ms: float = 0.0,
        retry_count: int = 0,
    ) -> "RestClientResult":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            error_context=error_context,
            duration_ms=duration_ms,
            retry_count=retry_count,
        )
