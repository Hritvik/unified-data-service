"""
Ticket resolution entities module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from common_utils.enums import GenerationType, OutputSchemaName
from common_utils.models.entities import BasePrismModel
from common_utils.models.model_bridge.native import (
    InvocationDetails,
    InvocationSummary,
)
from common_utils.timezone_utils import format_datetime_to_standard_format


class EvaluationResult(BaseModel):
    # Basic ticket information
    ticket_id: str = Field(..., description="Ticket ID")
    ticket_description: str = Field(..., description="Ticket description")
    agent_disposition: str = Field(..., description="Agent selected L2 disposition")
    supplier_sub_category_id: int = Field(..., description="Supplier sub-category ID")
    supplier_sub_category_title: Optional[str] = Field(
        ..., description="Supplier sub-category title"
    )
    supplier_category_id: Optional[int] = Field(
        None, description="Supplier category ID"
    )
    supplier_category_title: Optional[str] = Field(
        None, description="Supplier category title"
    )

    # Agent information
    agent_sub_category_id: Optional[int] = Field(
        None, description="Agent sub-category ID"
    )
    agent_sub_category_title: Optional[str] = Field(
        None, description="Agent sub-category title"
    )
    agent_category_id: Optional[int] = Field(None, description="Agent category ID")
    agent_category_title: Optional[str] = Field(
        None, description="Agent category title"
    )

    # Error information
    error_occurred: bool = Field(..., description="Whether an error occurred")
    error_code: Optional[int] = Field(None, description="Error code if error occurred")
    error_detail: Optional[str] = Field(
        None, description="Detailed error message if error occurred"
    )

    # Detection results (only populated when error_occurred=False)
    detected_issue_category_ids: Optional[List[int]] = Field(
        None,
        description="List of detected issue category IDs (primary first, then alternatives)",
    )
    detected_issue_category_titles: Optional[List[str]] = Field(
        None,
        description="List of detected issue category titles (primary first, then alternatives)",
    )
    issue_category_result: Optional["IssueCategoryResult"] = Field(
        None, description="Full issue category result"
    )
    detected_intent: Optional[List[int]] = Field(
        None, description="Detected intent IDs"
    )
    detected_sub_category_ids: Optional[List[int]] = Field(
        None, description="Detected sub-category IDs"
    )
    detected_sub_category_titles: Optional[List[str]] = Field(
        None, description="Detected sub-category titles"
    )
    faq_result: Optional["FAQResult"] = Field(None, description="Full FAQ result")

    # Evaluation metrics
    agent_supplier_match: Optional[bool] = Field(
        None, description="Whether agent and supplier selections match"
    )
    agent_model_match: Optional[bool] = Field(
        None, description="Whether agent selection matches model prediction"
    )
    multiple_faq_detected: Optional[bool] = Field(
        None, description="Whether multiple FAQs were detected"
    )
    ic_faq_scenario: Optional[str] = Field(
        None, description="IC/FAQ scenario classification"
    )


class SimpleAgentInput(BaseModel):
    """Input model for the simple agent"""

    request_id: str = Field(..., description="Request ID")
    template_namespace: str = Field(..., description="Template namespace")
    template_name: str = Field(..., description="Template name")
    route_plan_name: str = Field(..., description="Route plan name")
    temperature: float = Field(..., description="Temperature")
    output_schema_name: OutputSchemaName = Field(
        default=None, description="Output schema name"
    )
    kwargs: Dict[str, Any] = Field(
        ..., description="Additional keyword arguments for template"
    )


class ClassificationFailureDetails(BaseModel):
    error_code: int = Field(..., description="Error code")


class ClassificationSuccessDetails(BaseModel):
    classification: List[int] = Field(..., description="Classification result")
    confidence_score: float = Field(..., description="Confidence score")

    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Ensure confidence score is between 0 and 1"""
        return max(0.0, min(1.0, v))


class ClassificationReasoningSteps(BaseModel):
    """Reasoning steps with input assessment and decision rationale"""

    input_assessment: str = Field(..., description="Assessment of the input")
    decision_rationale: str = Field(..., description="Rationale for the decision")


class ClassificationMetadata(BaseModel):
    """Metadata including quality metrics and analysis"""

    redundant_ticket_description: bool = Field(
        ..., description="Whether the ticket description is redundant"
    )
    input_quality_score: float = Field(..., description="Quality score of the input")
    ambiguity_level: str = Field(..., description="Level of ambiguity in the input")
    key_themes_identified: List[str] = Field(
        ..., description="Key themes identified in the input"
    )
    viable_options: List[int] = Field(..., description="Viable classification options")


class SimpleAgentOutput(BaseModel):
    """Output model for the simple agent"""

    output_schema_name: Optional[OutputSchemaName] = Field(
        default=None, description="Output schema name"
    )
    invocation_journey: Optional[List[InvocationDetails]] = Field(
        default=None, description="Invocation journey from model bridge"
    )
    invocation_summary: Optional[InvocationSummary] = Field(
        default=None, description="Invocation summary from model bridge"
    )


class EvaluationClassifierOutput(SimpleAgentOutput):
    """Dynamic output model for the classifier agent that adapts to different response structures"""

    success: bool = Field(..., description="Whether the classification was successful")
    failure_details: Optional[ClassificationFailureDetails] = Field(
        default=None, description="Details of the failure if not successful"
    )
    success_details: Optional[ClassificationSuccessDetails] = Field(
        default=None, description="Details of the success if successful"
    )
    reasoning_steps: Optional[ClassificationReasoningSteps] = Field(
        default=None, description="Reasoning steps for the classification"
    )
    metadata: Optional[ClassificationMetadata] = Field(
        default=None, description="Metadata including quality metrics and analysis"
    )

    @classmethod
    def create_error_response(
        cls, explanation: str = "Failed to classify intent"
    ) -> "EvaluationClassifierOutput":
        """Create an error response with default values"""
        return cls(
            output_schema_name=OutputSchemaName.EVALUATION_CLASSIFIER,
            success=False,
            failure_details=ClassificationFailureDetails(error_code=-3),
        )


class ProductionClassifierOutput(SimpleAgentOutput):
    """Dynamic output model for the classifier agent that adapts to different response structures"""

    success: bool = Field(..., description="Whether the classification was successful")
    failure_details: Optional[ClassificationFailureDetails] = Field(
        default=None, description="Details of the failure if not successful"
    )
    success_details: Optional[ClassificationSuccessDetails] = Field(
        default=None, description="Details of the success if successful"
    )

    reasoning_steps: Optional[ClassificationReasoningSteps] = Field(
        default=None, description="Reasoning steps for the classification"
    )
    metadata: Optional[ClassificationMetadata] = Field(
        default=None, description="Metadata including quality metrics and analysis"
    )

    @classmethod
    def create_error_response(
        cls, explanation: str = "Failed to classify intent"
    ) -> "EvaluationClassifierOutput":
        """Create an error response with default values"""
        return cls(
            success=False, failure_details=ClassificationFailureDetails(error_code=-3)
        )


class ResponseGenerationFailureDetails(BaseModel):
    error_code: int = Field(..., description="Error code")
    failure_reason: str = Field(..., description="Failure reason")


class ResponseGenerationSuccessDetails(BaseModel):
    response: str = Field(..., description="Response")


class ResponseGenerationReasoningSteps(BaseModel):
    """Reasoning steps with input assessment and decision rationale"""

    output_rationale: str = Field(..., description="Reasoning for the output")


class ResponseGenerationMetadata(BaseModel):
    """Metadata including quality metrics and analysis"""

    output_script: Optional[str] = Field(default=None, description="Output script")
    output_language: Optional[str] = Field(default=None, description="Output language")


class ProductionResponseGenerationOutput(SimpleAgentOutput):
    """Dynamic output model for the classifier agent that adapts to different response structures"""

    success: bool = Field(..., description="Whether the classification was successful")
    failure_details: Optional[ResponseGenerationFailureDetails] = Field(
        default=None, description="Details of the failure if not successful"
    )
    success_details: Optional[ResponseGenerationSuccessDetails] = Field(
        default=None, description="Details of the success if successful"
    )
    reasoning_steps: Optional[ResponseGenerationReasoningSteps] = Field(
        default=None, description="Reasoning steps for the classification"
    )
    metadata: Optional[ResponseGenerationMetadata] = Field(
        default=None, description="Metadata including quality metrics and analysis"
    )

    @classmethod
    def create_error_response(
        cls, explanation: str = "Failed to generate response"
    ) -> "ProductionResponseGenerationOutput":
        """Create an error response with default values"""
        return cls(
            success=False,
            failure_details=ResponseGenerationFailureDetails(error_code=-3),
            failure_reason=explanation,
        )


class ProductionSummaryGenerationOutput(SimpleAgentOutput):
    """Dynamic output model for the classifier agent that adapts to different response structures"""

    success: bool = Field(..., description="Whether the classification was successful")
    failure_details: Optional[ResponseGenerationFailureDetails] = Field(
        default=None, description="Details of the failure if not successful"
    )
    success_details: Optional[ResponseGenerationSuccessDetails] = Field(
        default=None, description="Details of the success if successful"
    )
    metadata: Optional[ResponseGenerationMetadata] = Field(
        default=None, description="Metadata including quality metrics and analysis"
    )

    @classmethod
    def create_error_response(
        cls, explanation: str = "Failed to generate summary"
    ) -> "ProductionSummaryGenerationOutput":
        """Create an error response with default values"""
        return cls(
            success=False,
            failure_details=ResponseGenerationFailureDetails(error_code=-3),
            failure_reason=explanation,
        )


class ICSelectionFailureDetails(BaseModel):
    """Failure details for IC selection."""

    error_code: int = Field(..., description="Error code")


class ICSelectionSuccessDetails(BaseModel):
    """Success details for IC selection."""

    selected_ic_id: Optional[int] = Field(
        None, description="ID of selected IC if selecting existing"
    )
    suggested_ic: Optional[Dict[str, str]] = Field(
        None, description="Suggested new IC with title and description"
    )
    confidence_score: float = Field(..., description="Confidence score")

    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Ensure confidence score is between 0 and 1"""
        return max(0.0, min(1.0, v))


class ICSelectionOutput(SimpleAgentOutput):
    """Output model for IC selection/suggestion."""

    success: bool = Field(..., description="Whether the selection was successful")
    failure_details: Optional[ICSelectionFailureDetails] = Field(
        default=None, description="Details of the failure if not successful"
    )
    success_details: Optional[ICSelectionSuccessDetails] = Field(
        default=None, description="Details of the success if successful"
    )
    reasoning_steps: Optional[ClassificationReasoningSteps] = Field(
        default=None, description="Reasoning steps for the selection"
    )

    @classmethod
    def create_error_response(
        cls, explanation: str = "Failed to select IC"
    ) -> "ICSelectionOutput":
        """Create an error response with default values"""
        return cls(
            output_schema_name=OutputSchemaName.IC_SELECTION,
            success=False,
            failure_details=ICSelectionFailureDetails(error_code=-3),
        )


class FAQSelectionFailureDetails(BaseModel):
    """Failure details for FAQ selection."""

    error_code: int = Field(..., description="Error code")


class FAQSelectionSuccessDetails(BaseModel):
    """Success details for FAQ selection."""

    selected_faq_id: Optional[int] = Field(
        None, description="ID of selected FAQ if selecting existing"
    )
    suggested_faq: Optional[Dict[str, str]] = Field(
        None, description="Suggested new FAQ with title and description"
    )
    confidence_score: float = Field(..., description="Confidence score")

    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Ensure confidence score is between 0 and 1"""
        return max(0.0, min(1.0, v))


class FAQSelectionOutput(SimpleAgentOutput):
    """Output model for FAQ selection/suggestion."""

    success: bool = Field(..., description="Whether the selection was successful")
    failure_details: Optional[FAQSelectionFailureDetails] = Field(
        default=None, description="Details of the failure if not successful"
    )
    success_details: Optional[FAQSelectionSuccessDetails] = Field(
        default=None, description="Details of the success if successful"
    )
    reasoning_steps: Optional[ClassificationReasoningSteps] = Field(
        default=None, description="Reasoning steps for the selection"
    )

    @classmethod
    def create_error_response(
        cls, explanation: str = "Failed to select FAQ"
    ) -> "FAQSelectionOutput":
        """Create an error response with default values"""
        return cls(
            output_schema_name=OutputSchemaName.FAQ_SELECTION,
            success=False,
            failure_details=FAQSelectionFailureDetails(error_code=-3),
        )


class IssueCategoryResult(BaseModel):
    error_occurred: bool = Field(..., description="Whether an error occurred")
    error_code: Optional[int] = Field(None, description="Error code if error occurred")
    error_detail: Optional[str] = Field(
        None, description="Detailed error message if error occurred"
    )

    # Success fields (only populated when error_occurred=False)
    detected_issue_category_ids: Optional[List[int]] = Field(
        None,
        description="List of detected issue category IDs (primary first, then alternatives)",
    )
    detected_issue_category_confidence_score: Optional[float] = Field(
        None, description="Confidence score for the primary classification"
    )
    detected_issue_category_reasoning_steps: Dict[str, Any] = Field(
        default_factory=dict, description="Reasoning steps for the classification"
    )
    detected_issue_category_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata for the classification"
    )

    # LLM invocation data
    invocation_journey: Optional[List[InvocationDetails]] = Field(
        default=None, description="LLM invocation journey details"
    )
    invocation_summary: Optional[InvocationSummary] = Field(
        default=None, description="LLM invocation summary"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()


class FAQResult(BaseModel):
    error_occurred: bool = Field(..., description="Whether an error occurred")
    error_code: Optional[int] = Field(None, description="Error code if error occurred")
    error_detail: Optional[str] = Field(
        None, description="Detailed error message if error occurred"
    )

    # Success fields (only populated when error_occurred=False)
    detected_intent: Optional[List[int]] = Field(
        None, description="List of detected intent IDs"
    )
    detected_intent_confidence_score: Optional[float] = Field(
        None, description="Confidence score for the classification"
    )
    detected_intent_reasoning_steps: Dict[str, Any] = Field(
        default_factory=dict, description="Reasoning steps for the classification"
    )
    detected_intent_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata for the classification"
    )

    # LLM invocation data
    invocation_journey: Optional[List[InvocationDetails]] = Field(
        default=None, description="LLM invocation journey details"
    )
    invocation_summary: Optional[InvocationSummary] = Field(
        default=None, description="LLM invocation summary"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()


class IntentClassificationResult(BaseModel):
    """
    Internal model for intent classification results.

    This model is used internally by services and contains the full internal models
    for both issue category and FAQ results. Conversion to response models should
    happen in the caller service.
    """

    error_occurred: bool = Field(..., description="Whether an error occurred")
    error_code: Optional[int] = Field(None, description="Error code if error occurred")
    error_detail: Optional[str] = Field(
        None, description="Detailed error message if error occurred"
    )

    # Success fields (only populated when error_occurred=False)
    issue_category_result: Optional[IssueCategoryResult] = Field(
        None, description="Full issue category result (internal model)"
    )
    faq_result: Optional[FAQResult] = Field(
        None, description="Full FAQ result (internal model)"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump()


class ErrorDetail(BaseModel):
    message: str = Field(..., description="Error message")


class BaseResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    error_detail: Optional[ErrorDetail] = Field(None, description="Error detail")
    data: Optional[Any] = Field(None, description="Data")


class FAQ(BaseModel):
    faq_id: str = Field(..., description="FAQ ID")
    faq_title: str = Field(..., description="FAQ title")
    issue_category_id: int = Field(..., description="Issue category ID")
    issue_category_title: str = Field(..., description="Issue category title")


class EvaluationInput(BaseModel):
    """Pydantic model for evaluation input with proper type definitions."""

    ticket_id: str = Field(..., description="Ticket ID")
    supplier_sub_category_id: int = Field(
        ..., description="Supplier selected sub-category ID"
    )
    agent_disposition: str = Field(..., description="Agent selected L2 disposition")
    ticket_description: str = Field(..., description="Ticket description")
    request_timestamp: str = Field(..., description="Request timestamp")
    request_type: str = Field(..., description="Request type")


class ResponseTemplateEntity(BaseModel):
    """Entity model for response template data stored in memory."""

    id: str = Field(..., description="Template ID")
    scenario_identifier: str = Field(
        ..., description="Unique identifier for the scenario"
    )
    scenario_description: str = Field(..., description="Description of the scenario")
    response_template: str = Field(..., description="Template for generating responses")
    summary_template: str = Field(..., description="Template for generating summaries")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    links: Optional[Dict[str, Any]] = Field(
        None, description="Optional links associated with the template"
    )

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )


class TrsInstrumentationRecord(BasePrismModel):
    """Pydantic model for metabase records."""

    success: bool = Field(..., description="Success flag")
    error_details: Dict[str, Any] = Field(
        ..., description="Error details in JSON format"
    )
    request_timestamp: str = Field(..., description="Request timestamp")
    faq_classification_identifier: str = Field(
        ..., description="FAQ classification identifier"
    )
    # LLM call data
    llm_call_journey: List[Dict[str, Any]] = Field(
        ..., description="LLM call journey data in JSON format"
    )
    llm_call_stats: Dict[str, Any] = Field(
        ..., description="LLM call statistics in JSON format"
    )

    # Request and identification fields
    request_type: str = Field(..., description="Type of request")
    supplier_id: Optional[int] = Field(None, description="Supplier identifier")
    ticket_id: Optional[str] = Field(None, description="Ticket identifier")
    # Supplier selected categories
    supplier_selected_issue_category_id: int = Field(
        ..., description="Supplier selected issue category ID"
    )
    supplier_selected_issue_category_title: str = Field(
        ..., description="Supplier selected issue category title"
    )
    supplier_selected_sub_category_id: int = Field(
        ..., description="Supplier selected sub-category ID"
    )
    supplier_selected_sub_category_title: str = Field(
        ..., description="Supplier selected sub-category title"
    )

    # Ticket information
    ticket_description: str = Field(..., description="Ticket description text")

    # Detected categories (as JSON arrays)
    detected_issue_category_id: List[int] = Field(
        ..., description="Detected issue category IDs in JSON format"
    )
    detected_issue_category_title: List[str] = Field(
        ..., description="Detected issue category titles in JSON format"
    )
    detected_sub_category_id: List[int] = Field(
        ..., description="Detected sub-category IDs in JSON format"
    )
    detected_sub_category_title: List[str] = Field(
        ..., description="Detected sub-category titles in JSON format"
    )

    # Metadata fields
    detected_issue_category_metadata: Dict[str, Any] = Field(
        ..., description="Detected issue category metadata in JSON format"
    )
    detected_sub_category_metadata: Dict[str, Any] = Field(
        ..., description="Detected sub-category metadata in JSON format"
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


class TicketResolutionInstrumentationRecord(BasePrismModel):
    """Pydantic model for metabase records."""

    success: bool = Field(..., description="Success flag")
    error_details: Dict[str, Any] = Field(
        ..., description="Error details in JSON format"
    )
    request_timestamp: str = Field(..., description="Request timestamp")
    llm_call_journey: List[Dict[str, Any]] = Field(
        ..., description="LLM call journey data in JSON format"
    )
    llm_call_stats: Dict[str, Any] = Field(
        ..., description="LLM call statistics in JSON format"
    )

    ticket_id: str = Field(..., description="Ticket ID")
    request: Dict[str, Any] = Field(..., description="Request context in JSON format")
    response: str = Field(..., description="Response")
    generation_type: GenerationType = Field(..., description="Generation type")
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


class TicketSummaryScenarioLLMInput(BaseModel):
    """Input model for the ticket summary LLM"""

    entity_responses: List[str] = Field(..., description="Entity responses")
    scenario_background: str = Field(..., description="Scenario background")
