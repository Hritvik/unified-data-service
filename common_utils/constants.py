"""
Application-wide constants.

This module contains constants that are used across different modules
in the application including error codes, API configurations, and endpoints.
"""


class ErrorCodes:
    """Error codes used throughout the application."""

    LLM_FOUND_NO_MATCH = -1
    LLM_FOUND_INSUFFICIENT_CONTEXT = -2

    SYSTEM_ERROR = -3
    PRE_CHECK_FAILED = -4
    CMB_DETECTED = -11

    FAQ_CLASSIFICATION_NO_MATCH_FOUND = -5
    FAQ_CLASSIFICATION_INSUFFICIENT_CONTEXT_ERROR = -6
    FAQ_CLASSIFICATION_LOW_CONFIDENCE = -7

    IC_CLASSIFICATION_NO_MATCH_FOUND = -8
    IC_CLASSIFICATION_INSUFFICIENT_CONTEXT_ERROR = -9
    IC_CLASSIFICATION_LOW_CONFIDENCE = -10

    ERROR_CODES = {
        SYSTEM_ERROR: "System Error",
        PRE_CHECK_FAILED: "Pre Check Failed",
        LLM_FOUND_NO_MATCH: "No Match Found",
        LLM_FOUND_INSUFFICIENT_CONTEXT: "Insufficient Context",
        FAQ_CLASSIFICATION_NO_MATCH_FOUND: "FAQ No Match Found",
        FAQ_CLASSIFICATION_INSUFFICIENT_CONTEXT_ERROR: "FAQ Insufficient Context",
        FAQ_CLASSIFICATION_LOW_CONFIDENCE: "FAQ Low Confidence",
        IC_CLASSIFICATION_NO_MATCH_FOUND: "IC No Match Found",
        IC_CLASSIFICATION_INSUFFICIENT_CONTEXT_ERROR: "IC Insufficient Context",
        IC_CLASSIFICATION_LOW_CONFIDENCE: "IC Low Confidence",
    }


class API:
    """API-related constants."""

    PREFIX = "/api/1.0/modelswitch"
    VERSION = "1.0.0"
    SERVICE_NAME = "ModelSwitch API"


class Endpoints:
    """API endpoint paths."""

    HEALTH = "/health"
    METRICS = "/metrics"
    MANIFEST_METRICS = "/manifest/metrics"

    # App endpoints
    ECHO = f"{API.PREFIX}/app/echo"

    # Cache endpoints
    CACHE_REFRESH = f"{API.PREFIX}/admin/cache/refresh"
    CACHE_STATUS = f"{API.PREFIX}/admin/cache/status"
    CACHE_SERVICES = f"{API.PREFIX}/admin/cache/services"

    # Ticket Resolution endpoints
    INTENT_DETECTION = f"{API.PREFIX}/ticket-resolution/intent-detection"
    RESPONSE_GENERATION = f"{API.PREFIX}/ticket-resolution/response-generation"
    ISSUE_CATEGORIES = f"{API.PREFIX}/ticket-resolution/issue-categories"
    IC_SUBCATEGORY = f"{API.PREFIX}/ticket-resolution/ic-subcategory"
    DISPOSITION_SC = f"{API.PREFIX}/ticket-resolution/disposition-sc"
    EVALUATION = f"{API.PREFIX}/ticket-resolution/evaluation"
    RESPONSE_TEMPLATES = f"{API.PREFIX}/ticket-resolution/response-templates"

    # Model Bridge endpoints
    MODEL_BRIDGE = f"{API.PREFIX}/admin/model-bridge"

    # REST Client endpoints
    REST_CLIENT = f"{API.PREFIX}/admin/rest-client"

    # Legacy registry endpoint constants (model_bridge_registry,
    # rest_client_registry, prompt_registry) were dropped when the V2
    # unified registry layer took over — V2 routes are mounted from
    # `config/registries/*/*.yaml` `controller.base_path` at startup.


class HTTPStatus:
    """HTTP status codes."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class Timeouts:
    """Default timeout values."""

    CONNECT_TIMEOUT = 30
    READ_TIMEOUT = 60
    WRITE_TIMEOUT = 60
    POOL_TIMEOUT = 30


class RetryConfig:
    """Retry configuration constants."""

    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2
    INITIAL_DELAY = 1
    MAX_DELAY = 60


class CacheConfig:
    """Cache configuration constants."""

    DEFAULT_TTL = 300  # 5 minutes
    MAX_TTL = 3600  # 1 hour
    MIN_TTL = 60  # 1 minute


class DatabaseConfig:
    """Database configuration constants."""

    DEFAULT_POOL_SIZE = 10
    MAX_POOL_SIZE = 100
    DEFAULT_TIMEOUT = 30
    MAX_TIMEOUT = 300


class DateTimeFormats:
    """DateTime format constants."""

    # Standard ISO format with timezone offset (same as BasePrismModel)
    ISO_FORMAT_WITH_TIMEZONE = "%Y-%m-%dT%H:%M:%S%z"

    # ISO format without timezone (for backward compatibility)
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"

    # Display formats
    DISPLAY_IST = "%Y-%m-%d %H:%M:%S IST"
    DISPLAY_UTC = "%Y-%m-%d %H:%M:%S UTC"


class PrismEventNames:
    """Prism event names."""

    FAQ_CLASSIFICATION_INSTRUMENTATION = "ticket_resolution_instrumentation"
    TICKET_RESOLUTION_INSTRUMENTATION = "ticket_resolution_response_instrumentation"
    MODEL_BRIDGE_INSTRUMENTATION = "model_bridge_instrumentation"
