"""
Error handling utilities for better exception information.
"""

import traceback
from typing import Any, Optional


def get_detailed_error_message(
    exception: Exception, include_traceback: bool = False
) -> str:
    """
    Get a detailed error message that includes the exception type and context.

    Args:
        exception: The exception that was raised
        include_traceback: Whether to include the full traceback

    Returns:
        A detailed error message string
    """
    exception_type = type(exception).__name__
    exception_message = str(exception)

    # Build detailed message
    if exception_message:
        detailed_message = f"{exception_type}: {exception_message}"
    else:
        detailed_message = f"{exception_type}"

    # Add traceback if requested
    if include_traceback:
        tb_lines = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        detailed_message += f"\nTraceback:\n{''.join(tb_lines)}"

    return detailed_message


def get_error_context(exception: Exception) -> dict[str, Any]:
    """
    Get comprehensive error context including type, message, and traceback.

    Args:
        exception: The exception that was raised

    Returns:
        Dictionary containing error context
    """
    return {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "traceback": traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ),
        "detailed_message": get_detailed_error_message(exception),
    }


def format_error_for_logging(
    exception: Exception, context: Optional[str] = None
) -> str:
    """
    Format an error message suitable for logging with optional context.

    Args:
        exception: The exception that was raised
        context: Optional context about where the error occurred

    Returns:
        Formatted error message for logging
    """
    error_msg = get_detailed_error_message(exception)

    if context:
        return f"{context}: {error_msg}"

    return error_msg


def format_error_for_response(
    exception: Exception, context: Optional[str] = None
) -> str:
    """
    Format an error message suitable for API responses (without sensitive info).

    Args:
        exception: The exception that was raised
        context: Optional context about where the error occurred

    Returns:
        Formatted error message for API responses
    """
    exception_type = type(exception).__name__
    exception_message = str(exception)

    # For certain exception types, provide more user-friendly messages
    if isinstance(exception, KeyError):
        error_msg = f"Missing required key: {exception_message}"
    elif isinstance(exception, AttributeError):
        error_msg = f"Missing attribute: {exception_message}"
    elif isinstance(exception, TypeError):
        error_msg = f"Type error: {exception_message}"
    elif isinstance(exception, ValueError):
        error_msg = f"Invalid value: {exception_message}"
    else:
        error_msg = (
            f"{exception_type}: {exception_message}"
            if exception_message
            else exception_type
        )

    if context:
        return f"{context}: {error_msg}"

    return error_msg
