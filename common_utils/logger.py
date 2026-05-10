"""
Unified logging utilities for the application.

This module provides logging setup and configuration that can be used
across different modules in the application with enhanced trace ID support.
"""

import logging
import sys
from typing import Any, Optional

try:
    from loguru import logger
except ImportError:
    # Fallback to standard logging
    logger = logging.getLogger(__name__)
    
    def get_logger(name: str):
        """Get logger instance."""
        try:
            from loguru import logger as loguru_logger
            return loguru_logger.bind(name=name)
        except ImportError:
            return logging.getLogger(name)


def _get_trace_id_from_context() -> str:
    """Get trace ID from context with fallback."""
    try:
        from .trace_context import get_current_trace_id

        trace_id = get_current_trace_id()
        return trace_id or "-"
    except ImportError:
        return "-"


def _get_clean_error_message(exception: Exception) -> str:
    """Get a clean, user-friendly error message from an exception."""
    if hasattr(exception, "__cause__") and exception.__cause__:
        # For chained rest_client, show the root cause
        root_cause = exception.__cause__
        while hasattr(root_cause, "__cause__") and root_cause.__cause__:
            root_cause = root_cause.__cause__
        return f"{type(exception).__name__}: {str(exception)} (caused by: {type(root_cause).__name__}: {str(root_cause)})"
    else:
        return f"{type(exception).__name__}: {str(exception)}"


def _safe_format_record(record: dict) -> dict:
    """Safely format log record to handle missing fields gracefully."""
    # Ensure extra exists
    if "extra" not in record:
        record["extra"] = {}

    # Ensure name exists in extra, fallback to module name
    if "name" not in record["extra"]:
        record["extra"]["name"] = record.get("module", "unknown")

    # Ensure trace_id exists in extra, fallback to N/A
    if "trace_id" not in record["extra"]:
        record["extra"]["trace_id"] = "-"

    return record


class TraceAwareLogger:
    """Logger wrapper that automatically includes trace ID in all log messages."""

    def __init__(self, name: Optional[str] = None):
        self.name = name or "app"
        self._logger = logger.bind(name=self.name)

    def _get_logger_with_trace(self) -> Any:
        """Get logger with current trace ID bound."""
        trace_id = _get_trace_id_from_context()
        # Only bind trace_id here
        return self._logger.bind(trace_id=trace_id).opt(depth=1)

    def _format_message_with_extra(self, message: str, **kwargs: Any) -> str:
        """Format message with extra fields appended."""
        if not kwargs:
            return message

        extra_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        return f"{message} | {extra_str}"

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with current trace ID."""
        formatted_message = self._format_message_with_extra(message, **kwargs)
        self._get_logger_with_trace().debug(formatted_message)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with current trace ID."""
        formatted_message = self._format_message_with_extra(message, **kwargs)
        self._get_logger_with_trace().info(formatted_message)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with current trace ID."""
        formatted_message = self._format_message_with_extra(message, **kwargs)
        self._get_logger_with_trace().warning(formatted_message)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with current trace ID."""
        formatted_message = self._format_message_with_extra(message, **kwargs)
        self._get_logger_with_trace().error(formatted_message)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with current trace ID."""
        formatted_message = self._format_message_with_extra(message, **kwargs)
        self._get_logger_with_trace().critical(formatted_message)

    def exception(
        self, message: str, exception: Optional[Exception] = None, **kwargs: Any
    ) -> None:
        """Log exception message with current trace ID and clean error details."""
        # Check if exc_info is True to preserve exception context
        exc_info = kwargs.pop("exc_info", False)

        if exception:
            clean_error = _get_clean_error_message(exception)
            full_message = f"{message} - {clean_error}"
        else:
            full_message = message

        formatted_message = self._format_message_with_extra(full_message, **kwargs)

        if exc_info:
            # Use the underlying loguru logger's exception method to preserve traceback
            # Get the raw loguru logger to avoid recursion
            raw_logger = self._logger.bind(trace_id=_get_trace_id_from_context())
            raw_logger.exception(formatted_message)
        else:
            # Use error() method for regular error logging
            self._get_logger_with_trace().error(formatted_message)


def enable_debug_logging() -> None:
    """Enable debug logging with detailed stack traces and diagnostics."""
    # Remove existing handlers
    logger.remove()

    # Add debug handler with full details
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <yellow>TraceID: {extra[trace_id]}</yellow> - <level>{message}</level>",
        level="DEBUG",
        colorize=True,
        backtrace=True,  # Enable full backtraces
        diagnose=True,  # Enable diagnostics
        enqueue=True,
        catch=True,  # Catch rest_client and enable proper caller detection
        filter=_safe_format_record,  # Apply safe formatting to all records
    )


def setup_loguru(
    format_string: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <yellow>TraceID: {extra[trace_id]}</yellow> - <level>{message}</level>",
    level: str = "INFO",
    backtrace: bool = False,  # Default to False for cleaner logs
    diagnose: bool = False,  # Default to False for cleaner logs
    enqueue: bool = True,
) -> Any:
    """
    Configure loguru logger with custom settings.

    Args:
        format_string: Log format string
        level: Logging level
        backtrace: Enable backtrace (default: False for cleaner logs)
        diagnose: Enable diagnose (default: False for cleaner logs)
        enqueue: Enable enqueue
    """

    # Remove default handler (if logger has remove method)
    try:
        logger.remove()
    except AttributeError:
        pass  # Method doesn't exist, ignore gracefully

    # Console handler with colored output
    logger.add(
        sys.stdout,
        format=format_string,
        level=level,
        colorize=True,
        backtrace=backtrace,
        diagnose=diagnose,
        enqueue=enqueue,
        catch=True,  # Catch rest_client and enable proper caller detection
        filter=_safe_format_record,  # Apply safe formatting to all records
    )

    return logger


def get_loguru_logger(name: Optional[str] = None) -> TraceAwareLogger:
    """Get a trace-aware logger instance."""
    return TraceAwareLogger(name)


def get_standard_logger(name: str) -> logging.Logger:
    """
    Get a standard Python logger instance for the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def setup_standard_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """
    Setup basic logging configuration.

    Args:
        level: Logging level
        format_string: Log format string
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - [TraceID: %(trace_id)s] - %(message)s"

    # Create a custom formatter that includes trace ID
    class TraceContextFormatter(logging.Formatter):
        def format(self, record):
            # Add trace_id to record if not present
            if not hasattr(record, "trace_id"):
                record.trace_id = _get_trace_id_from_context()
            return super().format(record)

    formatter = TraceContextFormatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


# Initialize loguru by default with clean logging
try:
    from app.config.settings import settings

    setup_loguru(
        format_string=settings.LOGURU_FORMAT,
        level=settings.LOGURU_LEVEL,
        backtrace=False,
        diagnose=False,
    )
except ImportError:
    # Fallback if settings not available
    setup_loguru(level="INFO", backtrace=False, diagnose=False)


def reload_logger_configuration() -> None:
    """Force reload the logger configuration with current settings."""
    try:
        from app.config.settings import settings

        setup_loguru(
            format_string=settings.LOGURU_FORMAT,
            level=settings.LOGURU_LEVEL,
            backtrace=False,
            diagnose=False,
        )
    except ImportError:
        # Fallback if settings not available
        pass


# Convenience function for backward compatibility
get_logger = get_loguru_logger


def is_debug_mode() -> bool:
    """Check if debug logging is enabled via LOGURU_LEVEL."""
    import os

    # Try to get from app settings first, then environment variable
    try:
        from app.config.settings import settings

        loguru_level = settings.LOGURU_LEVEL.upper()
    except ImportError:
        # Fallback to environment variable if settings not available
        loguru_level = os.getenv("LOGURU_LEVEL", "INFO").upper()

    return loguru_level == "DEBUG"


def setup_logging_for_environment() -> None:
    """Setup logging based on LOGURU_LEVEL from settings or environment."""
    import os

    # Try to get from app settings first, then environment variable
    try:
        from app.config.settings import settings

        loguru_level = settings.LOGURU_LEVEL.upper()
        loguru_format = settings.LOGURU_FORMAT
    except ImportError:
        # Fallback to environment variable if settings not available
        loguru_level = os.getenv("LOGURU_LEVEL", "INFO").upper()
        loguru_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <yellow>TraceID: {extra[trace_id]}</yellow> - <level>{message}</level> | <blue>{extra}</blue>"

    if loguru_level == "DEBUG":
        enable_debug_logging()
    else:
        # Use clean logging for INFO, WARNING, ERROR levels
        # Try to get backtrace and diagnose settings from app config
        try:
            from app.config.settings import settings

            backtrace = getattr(settings, "LOGURU_BACKTRACE", False)
            diagnose = getattr(settings, "LOGURU_DIAGNOSE", False)
        except ImportError:
            # Fallback to False if settings not available
            backtrace = False
            diagnose = False

        setup_loguru(
            format_string=loguru_format,
            level=loguru_level,
            backtrace=backtrace,
            diagnose=diagnose,
        )


def log_error_with_context(
    logger_instance: Any,
    message: str,
    error: Exception,
    context: Optional[dict[str, Any]] = None,
    include_traceback: bool = True,
) -> None:
    """
    Log error with consistent context and exception info.

    Args:
        logger_instance: The logger to use
        message: Error message
        error: The exception that occurred
        context: Additional context dictionary
        include_traceback: Whether to include traceback info
    """
    try:
        from .error_utils import get_error_context

        error_context = get_error_context(error)
        extra = context or {}
        extra.update(
            {
                "error_type": error_context["exception_type"],
                "error_message": error_context["exception_message"],
                "operation": context.get("operation", "unknown")
                if context
                else "unknown",
            }
        )

        if include_traceback:
            logger_instance.exception(message, **extra)
        else:
            logger_instance.error(message, **extra)

    except ImportError:
        # Fallback if error_utils not available
        extra = context or {}
        extra["error_type"] = type(error).__name__
        extra["error_message"] = str(error)

        if include_traceback:
            logger_instance.exception(message, **extra)
        else:
            logger_instance.error(message, **extra)


def log_operation_result(
    logger_instance: Any,
    operation: str,
    entity_id: str,
    success: bool,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log operation results consistently with structured data.

    Args:
        logger_instance: The logger to use
        operation: Name of the operation performed
        entity_id: ID of the entity being operated on
        success: Whether the operation succeeded
        details: Additional operation details
    """
    level = "info" if success else "error"
    extra = details or {}
    extra.update({"operation": operation, "entity_id": entity_id, "success": success})

    message = (
        f"Operation '{operation}' completed"
        if success
        else f"Operation '{operation}' failed"
    )
    getattr(logger_instance, level)(message, **extra)


def log_service_operation(
    logger_instance: Any,
    service_name: str,
    operation: str,
    entity_id: Optional[str] = None,
    success: bool = True,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log service operations with consistent structure.

    Args:
        logger_instance: The logger to use
        service_name: Name of the service
        operation: Name of the operation
        entity_id: Optional entity ID
        success: Whether operation succeeded
        details: Additional operation details
    """
    extra = details or {}
    extra.update({"service": service_name, "operation": operation, "success": success})

    if entity_id:
        extra["entity_id"] = entity_id

    level = "info" if success else "error"
    message = (
        f"{service_name}: {operation} completed"
        if success
        else f"{service_name}: {operation} failed"
    )

    getattr(logger_instance, level)(message, **extra)


def log_with_trace_context(
    logger_instance: Any, level: str, message: str, **kwargs: Any
) -> None:
    """
    Log a message with automatic trace context injection.

    This function automatically includes the current trace ID in the log entry
    without requiring manual context binding.

    Args:
        logger_instance: The logger to use
        level: Log level (debug, info, warning, error, critical)
        message: The message to log
        **kwargs: Additional context to include in the log
    """
    # Get current trace ID from context
    trace_id = _get_trace_id_from_context()

    # Bind trace_id to the logger instance
    bound_logger = logger_instance.bind(trace_id=trace_id)

    # Log the message with the specified level
    getattr(bound_logger, level)(message, **kwargs)
