"""
Model bridge native models module.

This module provides native models with business logic for the model bridge.
These models serve as the core business logic layer between documents and API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field

from common_utils.enums import (
    APIContract,
    AttributeMatchSelectionStrategy,
    Format,
    InvocationAttemptFailureReason,
    InvocationAttemptResult,
    InvocationFailureReason,
    InvocationStatus,
    Modality,
    ModelBridgeContractType,
    RoutingStrategy,
    SelectionStrategy,
)
from common_utils.models.entities import BasePrismModel
from common_utils.timezone_utils import format_datetime_to_standard_format, get_utc_now


class ModelInfoNative(BaseModel):
    """Native model information with business logic."""

    model_name: str = Field(..., description="Model name")
    filter_attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Filter attributes"
    )
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags")
    api_contract: APIContract = Field(..., description="API contract")
    input_modality: List[Modality] = Field(..., description="Input modalities")
    output_modality: List[Modality] = Field(..., description="Output modalities")
    input_format: Format = Field(..., description="Input format")
    output_format: Format = Field(..., description="Output format")
    is_active: bool = Field(default=True, description="Is active")
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @computed_field
    @property
    def is_multimodal(self) -> bool:
        """Check if this model supports multiple input modalities."""
        return len(self.input_modality) > 1

    @computed_field
    @property
    def is_multiformat(self) -> bool:
        """Check if this model supports multiple output formats."""
        return len(self.output_modality) > 1

    @computed_field
    @property
    def has_custom_tags(self) -> bool:
        """Check if this model has custom tags."""
        return bool(self.tags.get("custom_tags"))

    def get_tag_value(self, tag_name: str) -> Optional[Any]:
        """Get the value of a specific tag."""
        return self.tags.get(tag_name)

    def has_filter_attribute(self, attribute_name: str) -> bool:
        """Check if this model has a specific filter attribute."""
        return attribute_name in self.filter_attributes

    def get_filter_attribute(self, attribute_name: str) -> Optional[Any]:
        """Get a specific filter attribute by name."""
        return self.filter_attributes.get(attribute_name)

    def supports_modality(self, modality: Modality) -> bool:
        """Check if this model supports a specific modality."""
        return modality in self.input_modality

    def supports_format(self, format_type: Format) -> bool:
        """Check if this model supports a specific format."""
        return format_type == self.output_format

    def is_compatible_with(self, other_model: "ModelInfoNative") -> bool:
        """Check if this model is compatible with another model."""
        return (
            self.input_modality == other_model.input_modality
            and self.output_modality == other_model.output_modality
            and self.input_format == other_model.input_format
            and self.output_format == other_model.output_format
        )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "model_name": self.model_name,
            "filter_attributes": self.filter_attributes,
            "tags": self.tags,
            "api_contract": self.api_contract.value,
            "input_modality": [mod.value for mod in self.input_modality],
            "output_modality": [mod.value for mod in self.output_modality],
            "input_format": self.input_format.value,
            "output_format": self.output_format.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DeploymentInfoNative(BaseModel):
    """Native deployment information with business logic."""

    deployment_name: str = Field(..., description="Deployment name")
    filter_attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Filter attributes"
    )
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags")
    model_name: str = Field(..., description="Model name")
    tpm: int = Field(..., description="Tokens per minute")
    client_identifier: str = Field(..., description="Client identifier")
    path_identifier: str = Field(..., description="Path identifier")
    is_active: bool = Field(default=True, description="Is active")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @computed_field
    @property
    def is_high_capacity(self) -> bool:
        """Check if this deployment has high capacity (TPM > 1000)."""
        return self.tpm > 1000

    @computed_field
    @property
    def is_high_priority(self) -> bool:
        """Check if this deployment is high priority."""
        priority = self.tags.get("priority")
        return priority == "high" if priority else False

    def get_tag_value(self, tag_name: str) -> Optional[Any]:
        """Get the value of a specific tag."""
        return self.tags.get(tag_name)

    def has_filter_attribute(self, attribute_name: str) -> bool:
        """Check if this deployment has a specific filter attribute."""
        return attribute_name in self.filter_attributes

    def get_filter_attribute(self, attribute_name: str) -> Optional[Any]:
        """Get a specific filter attribute by name."""
        return self.filter_attributes.get(attribute_name)

    def can_handle_tpm(self, required_tpm: int) -> bool:
        """Check if this deployment can handle the required TPM."""
        return self.tpm >= required_tpm

    def is_available_for_client(self, client_id: str) -> bool:
        """Check if this deployment is available for a specific client."""
        return self.client_identifier == client_id or self.client_identifier == "*"

    def get_endpoint_path(self, base_path: str = "") -> str:
        """Get the endpoint path for this deployment."""
        return f"{base_path.rstrip('/')}/{self.path_identifier}"

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "deployment_name": self.deployment_name,
            "filter_attributes": self.filter_attributes,
            "tags": self.tags,
            "model_name": self.model_name,
            "tpm": self.tpm,
            "client_identifier": self.client_identifier,
            "path_identifier": self.path_identifier,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DeploymentConfig(BaseModel):
    """Deployment configuration for route planning."""

    name: str = Field(..., description="Deployment name")
    weight: float = Field(default=1.0, description="Deployment weight")
    priority: int = Field(default=0, description="Deployment priority")


class RouteLevelModelConfig(BaseModel):
    """Model configuration for route planning levels."""

    name: str = Field(..., description="Model name")
    weight: float = Field(default=1.0, description="Model weight")
    priority: int = Field(default=0, description="Model priority")
    deployments: List[DeploymentConfig] = Field(
        default_factory=list, description="Deployment configurations"
    )


class RoutePlanLevelNative(BaseModel):
    """Native route plan level with business logic."""

    level: int = Field(..., description="Level number")
    model_selection_strategy: SelectionStrategy = Field(
        ..., description="Model selection strategy"
    )
    deployment_selection_strategy: SelectionStrategy = Field(
        ..., description="Deployment selection strategy"
    )
    model_attribute_match_strategy: Optional[AttributeMatchSelectionStrategy] = Field(
        default=None, description="Model attribute match strategy"
    )
    deployment_attribute_match_strategy: Optional[
        AttributeMatchSelectionStrategy
    ] = Field(default=None, description="Deployment attribute match strategy")
    routing_strategy: RoutingStrategy = Field(
        ..., description="Routing strategy for deployment selection"
    )
    attributes: Optional[Dict[str, Any]] = Field(
        default=None, description="Attributes for attribute matching"
    )
    models: Optional[List[RouteLevelModelConfig]] = Field(
        default=None, description="Model configurations for explicit matching"
    )

    @computed_field
    @property
    def is_primary_level(self) -> bool:
        """Check if this is the primary routing level."""
        return self.level == 1

    @computed_field
    @property
    def has_strategy(self) -> bool:
        """Check if this level has a selection strategy defined."""
        return (
            self.model_selection_strategy is not None
            or self.deployment_selection_strategy is not None
        )

    def get_model_strategy_name(self) -> str:
        """Get the model selection strategy name."""
        return self.model_selection_strategy.name

    def get_deployment_strategy_name(self) -> str:
        """Get the deployment selection strategy name."""
        return self.deployment_selection_strategy.name


class RoutePlanRetryConfigNative(BaseModel):
    """Native route plan retry configuration with business logic."""

    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    max_time_seconds: int = Field(
        default=15, description="Maximum retry time in seconds"
    )
    strict_max_time: bool = Field(
        default=True, description="Whether to strictly enforce max time"
    )

    @computed_field
    @property
    def is_aggressive_retry(self) -> bool:
        """Check if this is an aggressive retry configuration."""
        return self.max_attempts > 3 and self.max_time_seconds > 60

    @computed_field
    @property
    def is_conservative_retry(self) -> bool:
        """Check if this is a conservative retry configuration."""
        return self.max_attempts <= 2 and self.max_time_seconds <= 30

    def can_retry(self, current_attempt: int, elapsed_time: int) -> bool:
        """Check if a retry is allowed based on current state."""
        if current_attempt >= self.max_attempts:
            return False

        if self.strict_max_time and elapsed_time >= self.max_time_seconds:
            return False

        return True

    def get_remaining_attempts(self, current_attempt: int) -> int:
        """Get the number of remaining retry attempts."""
        return max(0, self.max_attempts - current_attempt)

    def get_remaining_time(self, elapsed_time: int) -> int:
        """Get the remaining time for retries."""
        return max(0, self.max_time_seconds - elapsed_time)


class RoutePlanTimeoutConfigNative(BaseModel):
    """Native route plan timeout configuration with business logic."""

    timeout_seconds: int = Field(default=5, description="Timeout in seconds")

    @computed_field
    @property
    def is_short_timeout(self) -> bool:
        """Check if this is a short timeout configuration."""
        return self.timeout_seconds <= 30

    @computed_field
    @property
    def is_long_timeout(self) -> bool:
        """Check if this is a long timeout configuration."""
        return self.timeout_seconds > 120

    @computed_field
    @property
    def timeout_minutes(self) -> float:
        """Get timeout in minutes."""
        return self.timeout_seconds / 60.0

    def is_expired(self, elapsed_time: int) -> bool:
        """Check if the timeout has expired."""
        return elapsed_time >= self.timeout_seconds

    def get_remaining_time(self, elapsed_time: int) -> int:
        """Get the remaining time before timeout."""
        return max(0, self.timeout_seconds - elapsed_time)


class RoutePlanConfigurationNative(BaseModel):
    """Native route plan configuration with business logic."""

    levels: List[RoutePlanLevelNative] = Field(..., description="Route planning levels")
    retry_config: RoutePlanRetryConfigNative = Field(
        ..., description="Retry configuration"
    )
    timeout_config: RoutePlanTimeoutConfigNative = Field(
        ..., description="Timeout configuration"
    )

    @computed_field
    @property
    def has_multiple_levels(self) -> bool:
        """Check if this route plan has multiple levels."""
        return len(self.levels) > 1

    @computed_field
    @property
    def primary_level(self) -> Optional[RoutePlanLevelNative]:
        """Get the primary routing level (level 1)."""
        return self.get_level(1)

    def get_level(self, level_number: int) -> Optional[RoutePlanLevelNative]:
        """Get a specific level by number."""
        for level in self.levels:
            if level.level == level_number:
                return level
        return None

    def is_valid_configuration(self) -> bool:
        """Check if this route plan configuration is valid."""
        if not self.levels:
            return False

        # Check if levels are sequential starting from 1
        expected_levels = list(range(1, len(self.levels) + 1))
        actual_levels = [level.level for level in self.levels]
        return expected_levels == actual_levels


class RoutePlanInfoNative(BaseModel):
    """Native route plan information with business logic."""

    id: str = Field(..., description="Route plan ID")
    route_plan_name: str = Field(..., description="Route plan name")
    route_plan: RoutePlanConfigurationNative = Field(
        ..., description="Route plan configuration"
    )
    is_active: bool = Field(default=True, description="Is active")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @computed_field
    @property
    def is_complex_route(self) -> bool:
        """Check if this is a complex route plan."""
        return self.route_plan.has_multiple_levels

    @computed_field
    @property
    def has_retry_capability(self) -> bool:
        """Check if the route plan has retry capability."""
        return self.route_plan.retry_config.max_attempts > 1

    @computed_field
    @property
    def has_timeout_protection(self) -> bool:
        """Check if the route plan has timeout protection."""
        return self.route_plan.timeout_config.timeout_seconds > 0

    def get_level_configuration(
        self, level_number: int
    ) -> Optional[RoutePlanLevelNative]:
        """Get configuration for a specific level."""
        return self.route_plan.get_level(level_number)

    def can_handle_retry(self, current_attempt: int, elapsed_time: int) -> bool:
        """Check if the route plan can handle retry at current attempt and time."""
        retry_config = self.route_plan.retry_config
        if current_attempt >= retry_config.max_attempts:
            return False

        if (
            retry_config.max_time_seconds > 0
            and elapsed_time >= retry_config.max_time_seconds
        ):
            return False

        return True

    def is_timeout_expired(self, elapsed_time: int) -> bool:
        """Check if the timeout has expired."""
        timeout_config = self.route_plan.timeout_config
        return (
            timeout_config.timeout_seconds > 0
            and elapsed_time >= timeout_config.timeout_seconds
        )

    def get_remaining_retry_attempts(self, current_attempt: int) -> int:
        """Get the number of remaining retry attempts."""
        return max(0, self.route_plan.retry_config.max_attempts - current_attempt)

    def get_remaining_retry_time(self, elapsed_time: int) -> int:
        """Get the remaining time for retries in seconds."""
        retry_config = self.route_plan.retry_config
        if retry_config.max_time_seconds <= 0:
            return -1  # No time limit
        return max(0, retry_config.max_time_seconds - elapsed_time)

    def get_remaining_timeout_time(self, elapsed_time: int) -> int:
        """Get the remaining time before timeout in seconds."""
        timeout_config = self.route_plan.timeout_config
        if timeout_config.timeout_seconds <= 0:
            return -1  # No timeout
        return max(0, timeout_config.timeout_seconds - elapsed_time)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "route_plan_name": self.route_plan_name,
            "route_plan": self.route_plan.model_dump(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InvocationAttempt(BaseModel):
    """Invocation attempt information."""

    timestamp_ms: int = Field(..., description="Timestamp in milliseconds")
    attempt_sequence_number: int = Field(..., description="Attempt sequence number")
    model: str = Field(..., description="Model name")
    deployment: str = Field(..., description="Deployment name")
    result: InvocationAttemptResult = Field(..., description="Result of the attempt")
    reason: Optional[InvocationAttemptFailureReason] = Field(
        default=None, description="Reason for the result"
    )
    details: Optional[str] = Field(default=None, description="Details of the attempt")
    latency: float = Field(
        default=0.0, description="Latency of this attempt in seconds"
    )
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp_ms": self.timestamp_ms,
            "attempt_sequence_number": self.attempt_sequence_number,
            "model": self.model,
            "deployment": self.deployment,
            "result": self.result,
            "reason": self.reason,
            "latency": self.latency,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class ModelDeploymentSelections(BaseModel):
    """Model and deployment selections for routing strategies."""

    model: str = Field(..., description="Model name")
    deployments: List[str] = Field(..., description="List of deployment names")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "deployments": self.deployments,
        }


class InvocationClock(BaseModel):
    """Invocation clock information."""

    started_at_ms: int = Field(..., description="Start timestamp in milliseconds")
    updated_at_ms: int = Field(..., description="Last update timestamp in milliseconds")


class InvocationExecution(BaseModel):
    """Invocation execution information."""

    current_level: int = Field(..., description="Current invocation level")
    selected: Optional[str] = Field(default=None, description="Selected deployment")
    attempts: List[InvocationAttempt] = Field(
        default_factory=list, description="Invocation attempts"
    )


class ModelBridgeRequest(BaseModel):
    """Model request for core bridge functionality."""

    request_id: str = Field(..., description="Request ID")
    route_plan_name: str = Field(..., description="Name of the route plan to use")
    response_format: Format = Field(..., description="Response format")


class ChatCompletionRequest(ModelBridgeRequest):
    """Chat completion request."""

    contract_type: ModelBridgeContractType = ModelBridgeContractType.CHAT_COMPLETION
    messages: List[Dict[str, Any]] = Field(..., description="Messages")
    temperature: Optional[float] = Field(
        default=0.7, description="Temperature for response generation"
    )
    max_tokens: Optional[int] = Field(
        default=1000, description="Maximum tokens in response"
    )
    top_p: Optional[float] = Field(default=None, description="Top-p sampling parameter")
    top_k: Optional[int] = Field(default=None, description="Top-k sampling parameter")
    frequency_penalty: Optional[float] = Field(
        default=None, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=None, description="Presence penalty"
    )
    tools: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Tools to use"
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Tool choice specification"
    )

    # Claude-specific parameters
    anthropic_version: Optional[str] = Field(
        default=None, description="Anthropic API version"
    )
    system: Optional[str] = Field(default=None, description="System message for Claude")

    # Gemini-specific parameters
    candidate_count: Optional[int] = Field(
        default=None, description="Number of candidates to generate"
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None, description="Stop sequences for generation"
    )
    safety_settings: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Safety settings for Gemini"
    )


class InvocationDetails(BaseModel):
    """Invocation details."""

    model_name: str = Field(..., description="Model name")
    deployment_name: str = Field(..., description="Deployment name")
    status: bool = Field(default=True, description="Response status")
    error_message: Optional[str] = Field(
        default=None, description="Error message if any"
    )
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")
    latency: float = Field(..., description="Latency")
    timestamp: datetime = Field(..., description="Timestamp")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()


class UnifiedLLMResponse(BaseModel):
    contract_type: ModelBridgeContractType = Field(..., description="Contract type")
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")
    message: Optional[str] = Field(default=None, description="Response message")


class InvocationContext(BaseModel):
    """Invocation context for tracking invocation decisions and execution."""

    invocation_id: str = Field(..., description="Unique invocation identifier")
    status: InvocationStatus = Field(..., description="Invocation status")
    failure_reason: Optional[InvocationFailureReason] = Field(
        default=None, description="Failure reason"
    )
    clock: InvocationClock = Field(..., description="Clock information")
    execution: InvocationExecution = Field(..., description="Execution information")
    request_context: ModelBridgeRequest = Field(
        ..., description="Request context information"
    )
    adapted_response: Optional[UnifiedLLMResponse] = Field(
        default=None, description="Response"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()


class InvocationSummary(BaseModel):
    """Invocation summary."""

    success: bool = Field(..., description="Success")
    total_invocations: int = Field(..., description="Total invocations")
    total_successes: int = Field(..., description="Total successes")
    total_failures: int = Field(..., description="Total failures")
    average_latency: float = Field(..., description="Average latency in seconds")
    total_input_tokens: int = Field(..., description="Total input tokens")
    total_output_tokens: int = Field(..., description="Total output tokens")
    total_latency: float = Field(..., description="Total latency in seconds")
    total_tokens: int = Field(..., description="Total tokens")
    successful_model: Optional[str] = Field(
        default=None, description="Successful model"
    )
    successful_deployment: Optional[str] = Field(
        default=None, description="Successful deployment"
    )

    def get_default_dict(self) -> Dict[str, Any]:
        """Get default dictionary representation."""
        return {
            "success": False,
            "total_invocations": 0,
            "total_successes": 0,
            "total_failures": 0,
            "average_latency": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_latency": 0.0,
            "total_tokens": 0,
            "successful_model": None,
            "successful_deployment": None,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()


class ModelBridgeResponse(BaseModel):
    """Model response for core bridge functionality."""

    response: UnifiedLLMResponse = Field(..., description="Response")
    invocation_journey: List[InvocationDetails] = Field(
        ..., description="Invocation Journey"
    )
    invocation_summary: InvocationSummary = Field(..., description="Invocation summary")
    success: bool = Field(default=True, description="Success")
    error_message: Optional[str] = Field(
        default=None, description="Error message if any"
    )


class ChatCompletionResponse(UnifiedLLMResponse):
    """Chat completion response."""

    message: str = Field(..., description="Message")


class ModelBridgeInstrumentationRecord(BasePrismModel):
    """Pydantic model for metabase records."""

    success: bool = Field(..., description="Success flag")
    error_details: Dict[str, Any] = Field(
        ..., description="Error details in JSON format"
    )
    invocation_timestamp: str = Field(..., description="Invocation timestamp")
    invocation_id: str = Field(..., description="Invocation ID")
    invocation_type: str = Field(..., description="Invocation type")
    invocation_status: str = Field(..., description="Invocation status")
    invocation_details: Dict[str, Any] = Field(
        ..., description="Invocation details in JSON format"
    )
    invocation_summary: Dict[str, Any] = Field(
        ..., description="Invocation summary in JSON format"
    )

    # Miscellaneous data
    misc: Dict[str, Any] = Field(..., description="Miscellaneous data in JSON format")

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = self.model_dump(exclude_none=True, exclude={"id"})
        if hasattr(self, "id") and self.id is not None:
            data["_id"] = str(self.id)
        return data

    def to_dict_with_datetime_strings(self) -> Dict[str, Any]:
        """Convert model to dictionary with datetime fields as strings."""

        def convert_datetime_fields(obj: Any) -> Any:
            """Recursively convert datetime fields to strings in nested objects."""
            if isinstance(obj, dict):
                return {
                    key: convert_datetime_fields(value) for key, value in obj.items()
                }
            elif isinstance(obj, list):
                return [convert_datetime_fields(item) for item in obj]
            elif isinstance(obj, datetime):
                return format_datetime_to_standard_format(obj)
            else:
                return obj

        data = self.model_dump(exclude_none=True, exclude={"id"})
        if hasattr(self, "id") and self.id is not None:
            data["_id"] = str(self.id)

        # Convert datetime fields to strings
        return convert_datetime_fields(data)


class DeploymentHealthIdentity(BaseModel):
    """Deployment health identity information."""

    deployment: str = Field(..., description="Deployment name")
    model: str = Field(..., description="Model name")


class DeploymentHealthAvailability(BaseModel):
    """Deployment health availability information."""

    is_alive: bool = Field(..., description="Whether the deployment is alive")
    last_heartbeat_timestamp: int = Field(..., description="Last heartbeat timestamp")
    uptime_streak_sec: int = Field(..., description="Uptime streak in seconds")
    consecutive_failures: int = Field(..., description="Consecutive failures count")
    last_status_code: int = Field(..., description="Last status code")

    @computed_field
    @property
    def uptime_hours(self) -> float:
        """Get uptime in hours."""
        return self.uptime_streak_sec / 3600.0


class LatencyMetrics(BaseModel):
    """Latency metrics for deployment performance."""

    p50: float = Field(..., description="50th percentile latency")
    p90: float = Field(..., description="90th percentile latency")
    p99: float = Field(..., description="99th percentile latency")
    avg: float = Field(..., description="Average latency")
    stddev: float = Field(..., description="Standard deviation")
    jitter: float = Field(..., description="Jitter")


class ThroughputMetrics(BaseModel):
    """Throughput metrics for deployment performance."""

    rps: float = Field(..., description="Requests per second")
    tokens_per_sec: int = Field(..., description="Tokens per second")


class PerformanceMetrics(BaseModel):
    """Performance metrics for deployment health."""

    latency: LatencyMetrics = Field(..., description="Latency metrics")
    throughput: ThroughputMetrics = Field(..., description="Throughput metrics")


class ErrorBreakdown(BaseModel):
    """Error breakdown by type."""

    timeout: int = Field(..., description="Timeout errors")
    error_5xx: int = Field(alias="5xx", description="5xx errors")
    invalid_input: int = Field(..., description="Invalid input errors")
    rate_limited: int = Field(..., description="Rate limited errors")


class RetryMetrics(BaseModel):
    """Retry metrics for reliability."""

    retry_rate: float = Field(..., description="Retry rate")
    avg_retries_per_request: float = Field(
        ..., description="Average retries per request"
    )


class ReliabilityMetrics(BaseModel):
    """Reliability metrics for deployment health."""

    success_rate: float = Field(..., description="Success rate")
    error_rate: float = Field(..., description="Error rate")
    errors: ErrorBreakdown = Field(..., description="Error breakdown")
    retries: RetryMetrics = Field(..., description="Retry metrics")


class CapacityMetrics(BaseModel):
    """Capacity metrics for deployment health."""

    concurrent_requests: int = Field(..., description="Current concurrent requests")
    max_concurrent_limit: int = Field(..., description="Maximum concurrent limit")
    queue_depth: int = Field(..., description="Queue depth")
    in_flight_ratio: float = Field(..., description="In-flight ratio")
    rate_limited: bool = Field(..., description="Whether rate limited")
    rate_limit_reset_timestamp: Optional[int] = Field(
        None, description="Rate limit reset timestamp"
    )

    @computed_field
    @property
    def capacity_utilization(self) -> float:
        """Get capacity utilization ratio."""
        if self.max_concurrent_limit == 0:
            return 0.0
        return self.concurrent_requests / self.max_concurrent_limit

    @computed_field
    @property
    def has_queue_backlog(self) -> bool:
        """Check if there's a queue backlog."""
        return self.queue_depth > 0


class EconomicsMetrics(BaseModel):
    """Economics metrics for deployment health."""

    cost_per_token_usd: float = Field(..., description="Cost per token in USD")
    cost_per_request_usd: float = Field(..., description="Cost per request in USD")
    effective_cost_usd: float = Field(..., description="Effective cost in USD")
    cost_efficiency: float = Field(..., description="Cost efficiency percentage")


class UserFeedbackMetrics(BaseModel):
    """User feedback metrics for quality assessment."""

    positive: int = Field(..., description="Positive feedback count")
    negative: int = Field(..., description="Negative feedback count")
    score: float = Field(..., description="Feedback score")

    @computed_field
    @property
    def total_feedback(self) -> int:
        """Get total feedback count."""
        return self.positive + self.negative


class QualityMetrics(BaseModel):
    """Quality metrics for deployment health."""

    valid_response_rate: float = Field(..., description="Valid response rate")
    hallucination_rate: float = Field(..., description="Hallucination rate")
    schema_compliance_rate: float = Field(..., description="Schema compliance rate")
    user_feedback: UserFeedbackMetrics = Field(..., description="User feedback metrics")


class StabilityMetrics(BaseModel):
    """Stability metrics for deployment health."""

    latency_trend: str = Field(..., description="Latency trend")
    error_trend: str = Field(..., description="Error trend")
    last_spike_timestamp: int = Field(..., description="Last spike timestamp")
    consecutive_error_burst: int = Field(
        ..., description="Consecutive error burst count"
    )

    @computed_field
    @property
    def is_stable(self) -> bool:
        """Check if the deployment is stable."""
        return (
            self.latency_trend == "stable"
            and self.error_trend == "stable"
            and self.consecutive_error_burst == 0
        )

    @computed_field
    @property
    def has_latency_issues(self) -> bool:
        """Check if there are latency issues."""
        return self.latency_trend == "increasing"


class RoutingMetrics(BaseModel):
    """Routing metrics for deployment health."""

    traffic_share: float = Field(..., description="Traffic share")
    routing_score: float = Field(..., description="Routing score")
    exploration_weight: float = Field(..., description="Exploration weight")
    is_temporarily_disabled: bool = Field(
        ..., description="Whether temporarily disabled"
    )
    degraded_mode: bool = Field(..., description="Whether in degraded mode")
    last_marked_unhealthy: Optional[int] = Field(
        None, description="Last marked unhealthy timestamp"
    )
    cooldown_until: Optional[int] = Field(None, description="Cooldown until timestamp")

    @computed_field
    @property
    def is_healthy_for_routing(self) -> bool:
        """Check if healthy for routing."""
        return (
            not self.is_temporarily_disabled
            and not self.degraded_mode
            and self.routing_score > 0.5
        )

    @computed_field
    @property
    def is_in_cooldown(self) -> bool:
        """Check if in cooldown period."""
        if self.cooldown_until is None:
            return False
        # This would need current timestamp to be accurate
        return True  # Placeholder


class MetaInformation(BaseModel):
    """Meta information for deployment health."""

    updated_at: int = Field(..., description="Last updated timestamp")


class DeploymentHealthStatus(BaseModel):
    """Comprehensive deployment health status with business logic."""

    identity: DeploymentHealthIdentity = Field(..., description="Deployment identity")
    availability: DeploymentHealthAvailability = Field(
        ..., description="Availability metrics"
    )
    performance: PerformanceMetrics = Field(..., description="Performance metrics")
    reliability: ReliabilityMetrics = Field(..., description="Reliability metrics")
    capacity: CapacityMetrics = Field(..., description="Capacity metrics")
    economics: EconomicsMetrics = Field(..., description="Economics metrics")
    quality: QualityMetrics = Field(..., description="Quality metrics")
    stability: StabilityMetrics = Field(..., description="Stability metrics")
    routing: RoutingMetrics = Field(..., description="Routing metrics")
    meta: MetaInformation = Field(..., description="Meta information")

    @computed_field
    @property
    def overall_health_score(self) -> float:
        """Calculate overall health score (0-1)."""
        scores = [
            1.0 if self.availability.is_healthy else 0.0,
            1.0 if self.performance.is_performing_well else 0.5,
            1.0 if self.reliability.is_reliable else 0.0,
            1.0 if not self.capacity.is_at_capacity else 0.5,
            1.0 if self.economics.is_cost_effective else 0.5,
            1.0 if self.quality.is_high_quality else 0.5,
            1.0 if self.stability.is_stable else 0.5,
            1.0 if self.routing.is_healthy_for_routing else 0.0,
        ]
        return sum(scores) / len(scores)

    @computed_field
    @property
    def is_healthy_overall(self) -> bool:
        """Check if deployment is healthy overall."""
        return self.overall_health_score > 0.7

    @computed_field
    @property
    def is_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return (
            not self.availability.is_alive
            or self.reliability.has_high_error_rate
            or self.quality.has_quality_issues
            or self.stability.has_latency_issues
        )

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of deployment health status."""
        return {
            "overall_health_score": self.overall_health_score,
            "is_healthy": self.is_healthy_overall,
            "has_critical_issues": self.is_critical_issues,
            "availability_status": "healthy"
            if self.availability.is_healthy
            else "unhealthy",
            "performance_status": "good"
            if self.performance.is_performing_well
            else "poor",
            "reliability_status": "reliable"
            if self.reliability.is_reliable
            else "unreliable",
            "capacity_status": "normal"
            if not self.capacity.is_at_capacity
            else "at_capacity",
            "quality_status": "high" if self.quality.is_high_quality else "low",
            "stability_status": "stable" if self.stability.is_stable else "unstable",
            "routing_status": "healthy"
            if self.routing.is_healthy_for_routing
            else "unhealthy",
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()
