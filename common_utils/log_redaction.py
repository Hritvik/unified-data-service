import json
import re
from enum import Enum
from typing import Any, Dict

SENSITIVE_HEADERS_PATTERN = re.compile(
    r"(token|password|secret|key|authorization|api[_-]?key|credential|auth|cookie|set-cookie)",
    re.IGNORECASE,
)

SENSITIVE_BODY_FIELDS = re.compile(
    r"(password|passwd|token|access_token|refresh_token|secret|authorization|"
    r"api[_-]?key|credential|cookie|ssn|credit_card|credit_card_number|cvv|"
    r"card_number|social_security)",
    re.IGNORECASE,
)

_REDACTED = "***REDACTED***"

_NON_TEXT_CONTENT_TYPES = re.compile(
    r"(application/octet-stream|image/|audio/|video/|application/pdf|application/zip)",
    re.IGNORECASE,
)


def redact_headers(headers: Any) -> Dict[str, str]:
    """Redact sensitive header values. Accepts dicts, HttpHeaders, or other mappings."""
    if not headers:
        return {}
    # Support HttpHeaders (Pydantic model with .headers dict) or similar objects
    if hasattr(headers, "headers") and isinstance(headers.headers, dict):
        raw = headers.headers
    elif isinstance(headers, dict):
        raw = headers
    else:
        return {}
    return {
        k: _REDACTED if SENSITIVE_HEADERS_PATTERN.search(k) else v
        for k, v in raw.items()
    }


class _EnumSafeEncoder(json.JSONEncoder):
    """JSON encoder that handles Enum values and Pydantic models."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def _redact_sensitive_fields(obj: Any) -> Any:
    """Recursively redact sensitive fields in a JSON-like structure."""
    if isinstance(obj, dict):
        return {
            k: _REDACTED if SENSITIVE_BODY_FIELDS.search(k) else _redact_sensitive_fields(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_sensitive_fields(item) for item in obj]
    return obj


def sanitize_body_for_logging(
    body_str: str,
    max_body_log_bytes: int = 1000,
    content_type: str | None = None,
) -> str:
    """Redact sensitive fields and enforce size limits for log output.

    If body exceeds *max_body_log_bytes*, returns the body size instead of the content.
    """
    if not body_str or body_str in ("", "<error reading body>"):
        return body_str

    # Skip binary / non-text content types
    if content_type and _NON_TEXT_CONTENT_TYPES.search(content_type):
        return f"<binary content-type: {content_type}, size={len(body_str)} bytes>"

    # Size check — if too large, just report size
    if len(body_str) > max_body_log_bytes:
        return f"<body too large to log, size={len(body_str)} bytes>"

    # Attempt JSON redaction
    try:
        parsed = json.loads(body_str)
        redacted = _redact_sensitive_fields(parsed)
        return json.dumps(redacted, ensure_ascii=False, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        return body_str


def serialize_body(body: Any) -> str:
    """Serialize a request/response body to a JSON string."""
    if body is None:
        return ""
    try:
        compact = dict(ensure_ascii=False, separators=(",", ":"), cls=_EnumSafeEncoder)
        if isinstance(body, str):
            return json.dumps(json.loads(body), **compact)
        if isinstance(body, bytes):
            return json.dumps(json.loads(body.decode("utf-8")), **compact)
        if isinstance(body, (dict, list)):
            return json.dumps(body, **compact)
        if hasattr(body, "model_dump"):
            return json.dumps(body.model_dump(), **compact)
        return str(body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return str(body) if body else ""
