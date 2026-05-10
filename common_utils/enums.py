from enum import Enum


class Modality(str, Enum):
    """Supported modalities for model input/output."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class Format(str, Enum):
    """Supported exact output formats that models can produce."""

    # Text formats
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    CSV = "csv"
    TSV = "tsv"

    # Audio formats
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    AAC = "aac"
    OGG = "ogg"
    M4A = "m4a"

    # Image formats
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    SVG = "svg"
    BMP = "bmp"
    TIFF = "tiff"

    # Video formats
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    WMV = "wmv"
    FLV = "flv"
    WEBM = "webm"

    # Binary formats
    BASE64 = "base64"
    HEX = "hex"
    BINARY = "binary"

    # Code formats
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    SQL = "sql"
    BASH = "bash"
    POWERSHELL = "powershell"

    # Document formats
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    RTF = "rtf"


class ModelCapability(str, Enum):
    """Supported model capabilities."""

    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_ANALYSIS = "image_analysis"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_GENERATION = "audio_generation"


class ModelProvider(str, Enum):
    """Supported model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerStrategy(str, Enum):
    """Circuit breaker strategies."""

    NONE = "NONE"
    AIOBREAKER = "AIOBREAKER"


class RetryStrategyType(str, Enum):
    """Retry strategy types."""

    NO_RETRY = "NO_RETRY"
    FIXED_DELAY = "FIXED_DELAY"
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"
    EXPONENTIAL_BACKOFF_WITH_JITTER = "EXPONENTIAL_BACKOFF_WITH_JITTER"
    LINEAR_BACKOFF = "LINEAR_BACKOFF"
    CUSTOM = "CUSTOM"


class APIContract(str, Enum):
    """Supported API contracts for model providers."""

    # OpenAI API contracts
    OPENAI_CHAT_COMPLETION = "openai_chat_completion"

    # Anthropic Claude API contracts
    CLAUDE_CHAT = "claude_chat"

    # Google Gemini API contracts
    GEMINI_CHAT = "gemini_chat"

    # Azure OpenAI API contracts
    AZURE_OPENAI_CHAT = "azure_openai_chat"

    # AWS Bedrock API contracts
    AWS_BEDROCK_CLAUDE = "aws_bedrock_claude"
    AWS_BEDROCK_TITAN = "aws_bedrock_titan"

    # Cohere API contracts
    COHERE_GENERATE = "cohere_generate"
    COHERE_CHAT = "cohere_chat"
    COHERE_SUMMARIZE = "cohere_summarize"

    # Hugging Face API contracts
    HUGGINGFACE_TEXT_GENERATION = "huggingface_text_generation"
    HUGGINGFACE_CHAT = "huggingface_chat"


class ModelBridgeContractType(str, Enum):
    """Supported model bridge contract types."""

    CHAT_COMPLETION = "chat_completion"
    GENERATION = "generation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"


class ConfigSourceType(str, Enum):
    """Supported configuration source types."""

    MONGO = "mongo"
    YAML = "yaml"
    CUSTOM = "custom"


class SelectionStrategy(str, Enum):
    """Supported model selection strategies for route planning."""

    ATTRIBUTE_MATCH = "attribute_match"
    EXPLICIT_MATCH = "explicit_match"
    ANY_MATCH = "any_match"
    NO_MATCH = "no_match"


class AttributeMatchSelectionStrategy(str, Enum):
    """Supported attribute match selection strategies."""

    SUBSET_MATCH = "subset_match"
    NO_CONFLICT_MATCH = "no_conflict_match"
    AT_LEAST_ONE_MATCH = "at_least_one_match"
    AT_LEAST_ONE_MATCH_NO_CONFLICT = "at_least_one_match_no_conflict"


class RoutingStrategy(str, Enum):
    """Supported routing strategies for deployment selection."""

    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"
    PRIORITY_BASED = "priority_based"
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_ERRORS = "least_errors"
    LEAST_LATENCY_AND_ERRORS = "least_latency_and_errors"
    LEAST_CONNECTIONS_AND_ERRORS = "least_connections_and_errors"
    LEAST_LATENCY_AND_CONNECTIONS = "least_latency_and_connections"
    LEAST_LATENCY_AND_CONNECTIONS_AND_ERRORS = (
        "least_latency_and_connections_and_errors"
    )
    PARALLEL_RACE = "parallel_race"


class MetricType(Enum):
    """Types of metrics supported by the unified system."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class InvocationStatus(str, Enum):
    """Supported invocation statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

    def is_terminal(self) -> bool:
        """Check if this status is terminal (final state)."""
        return self in {self.COMPLETED, self.FAILED}


class InvocationAttemptResult(str, Enum):
    """Supported invocation attempt results."""

    SUCCESS = "success"
    FAILED = "failed"


class InvocationAttemptFailureReason(str, Enum):
    """Supported invocation attempt failure reasons."""

    MODEL_NOT_FOUND = "model_not_found"
    DEPLOYMENT_NOT_FOUND = "deployment_not_found"
    DEPLOYMENT_NOT_AVAILABLE = "deployment_not_available"
    DEPLOYMENT_TIMEOUT = "deployment_timeout"
    DEPLOYMENT_ERROR = "deployment_error"
    REQUEST_ADAPTER_ERROR = "request_adapter_error"
    RESPONSE_ADAPTER_ERROR = "response_adapter_error"
    PROVIDER_ERROR = "provider_error"
    PROVIDER_RATE_LIMIT = "provider_rate_limit"
    PROVIDER_QUOTA_EXCEEDED = "provider_quota_exceeded"
    PROVIDER_AUTHENTICATION_ERROR = "provider_authentication_error"
    PROVIDER_PERMISSION_ERROR = "provider_permission_error"
    PROVIDER_INVALID_REQUEST = "provider_invalid_request"
    PROVIDER_SERVICE_UNAVAILABLE = "provider_service_unavailable"
    PROVIDER_INTERNAL_ERROR = "provider_internal_error"


class InvocationFailureReason(str, Enum):
    """Supported invocation attempt failure reasons."""

    DEPLOYMENT_SELECTION_FAILURE = "deployment_selection_failure"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class StrategyType(str, Enum):
    """Enumeration of available strategy types."""

    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    COMBINED = "combined"


class ResponseGenerationType(str, Enum):
    """V2 API response generation types with consistent naming."""

    # Entity-level: raw input (from templates)
    ENTITY_RAW_MESSAGE = "entity_raw_message"
    ENTITY_RAW_FILE = "entity_raw_file"

    # Scenario-level: raw input (from templates)
    SCENARIO_RAW_MESSAGE = "scenario_raw_message"
    SCENARIO_RAW_FILE = "scenario_raw_file"

    # Scenario-level: entity input (summarization from entity responses)
    SCENARIO_FROM_ENTITIES_MESSAGE = "scenario_from_entities_message"
    SCENARIO_FROM_ENTITIES_FILE = "scenario_from_entities_file"

    # Ticket-level: raw input (from templates, aggregated by scenario from entity data)
    TICKET_RAW_MESSAGE = "ticket_raw_message"

    # Ticket-level: scenario input (summarization from scenario responses)
    TICKET_FROM_SCENARIOS_MESSAGE = "ticket_from_scenarios_message"

    # Ticket-level: entity input (summarization from entity responses)
    TICKET_FROM_ENTITIES_MESSAGE = "ticket_from_entities_message"

    @property
    def level(self) -> str:
        """Extract level: entity/scenario/ticket"""
        if self.value.startswith("entity"):
            return "entity"
        elif self.value.startswith("scenario"):
            return "scenario"
        elif self.value.startswith("ticket"):
            return "ticket"
        raise ValueError(f"Unknown level for {self.value}")

    @property
    def input_source(self) -> str:
        """Extract input source: raw/entity/scenario"""
        if "raw" in self.value:
            return "raw"
        elif "from_entities" in self.value:
            return "entity"
        elif "from_scenarios" in self.value:
            return "scenario"
        raise ValueError(f"Unknown input source for {self.value}")

    @property
    def output_format(self) -> str:
        """Extract output format: message/file"""
        return "file" if "file" in self.value else "message"


class GenerationType(str, Enum):
    """Legacy generation types (for v1 API backward compatibility)."""

    # Legacy
    TICKET_ENTITY_RESOLUTION = "ticket_entity_resolution"
    TICKET_RESOLUTION_SUMMARY = "ticket_resolution_summary"

    # Old enum values (mapped to ResponseGenerationType)
    RESOLUTION_TICKET_MESSAGE = "resolution_ticket_message"
    RESOLUTION_SCENARIO_MESSAGE = "resolution_scenario_message"
    RESOLUTION_SCENARIO_ATTACHMENT = "resolution_scenario_file_response"
    RESOLUTION_ENTITY_MESSAGE = "resolution_entity_message"
    RESOLUTION_ENTITY_ATTACHMENT = "resolution_entity_file_response"


class ErrorCategory(str, Enum):
    """Error categories for REST client error handling."""

    CONFIGURATION = "configuration"  # Non-recoverable, should fail fast
    NETWORK = "network"  # Potentially recoverable with retry
    TIMEOUT = "timeout"  # Potentially recoverable with retry
    DOWNSTREAM = "downstream"  # Depends on status code
    VALIDATION = "validation"  # Non-recoverable, should fail fast
    STRATEGY = "strategy"  # Circuit breaker, retry exhaustion


class OutputSchemaName(str, Enum):
    """Enumeration of available output schema names."""

    EVALUATION_CLASSIFIER = "evaluation_classifier"
    PRODUCTION_CLASSIFIER = "production_classifier"
    EVALUATION_RESPONSE_GENERATION = "evaluation_response_generation"
    PRODUCTION_RESPONSE_GENERATION = "production_response_generation"
    EVALUATION_TICKET_RESOLUTION_SUMMARY = "evaluation_ticket_resolution_summarisation"
    PRODUCTION_TICKET_RESOLUTION_SUMMARY = "production_ticket_resolution_summarisation"
    IC_SELECTION = "ic_selection"
    FAQ_SELECTION = "faq_selection"

    @classmethod
    def str_to_enum(cls, value: str) -> "OutputSchemaName":
        """
        Convert a string value to the corresponding OutputSchemaName enum member.

        Args:
            value: The string value to convert

        Returns:
            The corresponding OutputSchemaName enum member

        Raises:
            ValueError: If the string value doesn't match any enum member
        """
        try:
            return cls(value)
        except ValueError:
            valid_values = [member.value for member in cls]
            raise ValueError(
                f"Invalid OutputSchemaName value: '{value}'. "
                f"Valid values are: {valid_values}"
            ) from None
