"""
Trace context utilities for propagating trace IDs across async function calls.

This module provides utilities for managing trace IDs in an async context,
allowing trace IDs to be propagated across function calls within the same request.
"""

import asyncio
import contextvars
import os
import re
import uuid
from typing import Any, Callable, Optional, TypeVar

# Context variables for distributed tracing
_trace_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
_span_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_id", default=None
)
_parent_span_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "parent_span_id", default=None
)
_request_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)

T = TypeVar("T")


class TraceContext:
    """
    Context manager for distributed trace propagation in async environments.

    Manages trace_id, span_id, parent_span_id, and request_id for the duration
    of a request, making them available to all functions called within that context.
    """

    def __init__(
        self,
        trace_id: str,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        self.trace_id = trace_id
        self.span_id = span_id or generate_span_id()
        self.parent_span_id = parent_span_id
        self.request_id = request_id
        self._tokens: list = []

    def _set(self) -> None:
        self._tokens = [
            _trace_id_context.set(self.trace_id),
            _span_id_context.set(self.span_id),
            _parent_span_id_context.set(self.parent_span_id),
            _request_id_context.set(self.request_id),
        ]

    def _reset(self) -> None:
        for token in self._tokens:
            token.var.reset(token)
        self._tokens = []

    def __enter__(self) -> "TraceContext":
        self._set()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        self._reset()

    async def __aenter__(self) -> "TraceContext":
        self._set()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        self._reset()


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID from the context."""
    return _trace_id_context.get()


def get_current_span_id() -> Optional[str]:
    """Get the current span ID from the context."""
    return _span_id_context.get()


def get_current_parent_span_id() -> Optional[str]:
    """Get the current parent span ID from the context."""
    return _parent_span_id_context.get()


def get_current_request_id() -> Optional[str]:
    """Get the current request ID (e.g. Envoy x-request-id) from the context."""
    return _request_id_context.get()


def set_trace_id(trace_id: str) -> None:
    """Set the trace ID in the current context."""
    _trace_id_context.set(trace_id)


def clear_trace_id() -> None:
    """Clear the trace ID from the current context."""
    _trace_id_context.set(None)


def with_trace_id(trace_id: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to set a trace ID for the duration of a function call."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with TraceContext(trace_id):
                return func(*args, **kwargs)

        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            async with TraceContext(trace_id):
                return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def generate_trace_id() -> str:
    """Generate a new 32-hex-char trace ID (W3C compatible)."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate a new 16-hex-char span ID."""
    return os.urandom(8).hex()


# Matches UUID (with or without dashes) or 16/32 char hex strings
_VALID_TRACE_ID_RE = re.compile(
    r"^(?:[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}|[0-9a-fA-F]{16}|[0-9a-fA-F]{32})$"
)


def is_trace_id_valid(trace_id: str) -> bool:
    """Check if a trace ID is valid (UUID or 16/32 char hex)."""
    if not trace_id:
        return False
    return bool(_VALID_TRACE_ID_RE.match(trace_id))


def get_outgoing_trace_headers() -> dict[str, str]:
    """
    Build trace propagation headers for outgoing HTTP requests.

    Returns B3 multi-header and W3C traceparent headers using the current
    context's trace ID and a new span ID (since the outgoing call is a new span).
    The current span becomes the parent span for the downstream service.
    """
    trace_id = get_current_trace_id()
    if not trace_id:
        return {}

    current_span_id = get_current_span_id()
    request_id = get_current_request_id()

    # Generate a new span ID for the outgoing call
    outgoing_span_id = generate_span_id()

    # Normalize trace ID to 32-hex for W3C (pad 16-char B3 trace IDs)
    trace_id_hex = trace_id.replace("-", "")
    if len(trace_id_hex) == 16:
        trace_id_w3c = "0" * 16 + trace_id_hex
    else:
        trace_id_w3c = trace_id_hex

    headers: dict[str, str] = {
        # B3 multi-header propagation
        "x-b3-traceid": trace_id_hex,
        "x-b3-spanid": outgoing_span_id,
        "x-b3-sampled": "1",
        # W3C traceparent: version-traceid-parentid-flags
        "traceparent": f"00-{trace_id_w3c}-{outgoing_span_id}-01",
    }

    # Set parent span ID (our current span is the parent of the outgoing call)
    if current_span_id:
        headers["x-b3-parentspanid"] = current_span_id

    # Propagate request ID if present
    if request_id:
        headers["x-request-id"] = request_id

    return headers


# Convenience alias for backward compatibility
RequestTraceContext = TraceContext
