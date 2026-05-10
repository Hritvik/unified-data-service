"""
Ticket resolution requests module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common_utils.enums import GenerationType, ResponseGenerationType


class RequestTemplate(BaseModel):
    """Model for optional template fields in requests."""

    response_template: Optional[str] = Field(
        None, description="Template for generating responses"
    )
    summary_template: Optional[str] = Field(
        None, description="Template for generating summaries"
    )
    links: Optional[Dict[str, Any]] = Field(
        None, description="Optional links associated with the template"
    )


class Entity(BaseModel):
    """Model for individual entity within an SOP bucket."""

    id: str = Field(..., description="Unique identifier for the entity")
    attributes: Optional[dict] = Field(
        default_factory=dict, description="Entity-specific attributes"
    )
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override for this entity"
    )


class Scenario(BaseModel):
    """Model for SOP bucket containing entities and context."""

    scenario_id: str = Field(..., description="Unique identifier for the SOP bucket")
    entities: list[Entity] = Field(..., description="List of entities in the bucket")
    attributes: Optional[dict] = Field(
        default_factory=dict, description="Scenario-specific attributes"
    )
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override for this scenario"
    )


class TicketEntityResolutionAttributes(BaseModel):
    """Model for ticket entity resolution attributes."""

    scenarios: list[Scenario] = Field(
        ..., description="Scenarios to use for entity resolution"
    )


class SummaryEntity(BaseModel):
    """Model for individual entity within an SOP bucket."""

    id: str = Field(..., description="Unique identifier for the entity")
    response: str = Field(..., description="Response to use for entity")
    attributes: Optional[dict] = Field(
        default_factory=dict, description="Entity-specific attributes"
    )


class SummaryScenario(BaseModel):
    """Model for summary scenario."""

    scenario_id: str = Field(
        ..., description="Unique identifier for the summary scenario"
    )
    entities: list[SummaryEntity] = Field(
        ..., description="Entities to use for summary"
    )
    attributes: Optional[dict] = Field(
        default_factory=dict, description="Scenario-specific attributes"
    )
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override for this scenario"
    )


class TicketResolutionSummaryAttributes(BaseModel):
    """Model for ticket resolution summary attributes."""

    scenarios: list[SummaryScenario] = Field(
        ..., description="Scenarios to use for resolution summary"
    )


class GenerationData(BaseModel):
    """Model for generation attributes."""

    ticket_context: Dict[str, Any] = Field(..., description="Ticket context")
    ticket_entity_resolution: Optional[TicketEntityResolutionAttributes] = Field(
        None, description="Attributes for ticket entity resolution"
    )
    ticket_resolution_summary: Optional[TicketResolutionSummaryAttributes] = Field(
        None, description="Attributes for ticket resolution summary"
    )
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override at ticket level"
    )


class GenerateResponseRequest(BaseModel):
    """Request model for generate-response endpoint (v1 - for backward compatibility)."""

    generation_type: GenerationType = Field(
        ..., description="Type of generation to perform"
    )
    data: GenerationData = Field(..., description="Data for the generation")


# V2 Models with discriminated unions


class UnifiedEntityInput(BaseModel):
    """Entity: identifiers, attributes, and optional pre-filled entity_response.

    For raw_entities: entity_response is empty; generation fills it.
    For entity_responses: entity_response is pre-filled for summarization.
    """

    entity_identifiers: Dict[str, Any] = Field(
        ..., description="Identifiers for the entity (e.g. product_name)"
    )
    entity_attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Entity-specific attributes (e.g. quantity)"
    )
    entity_response: Optional[str] = Field(
        None,
        description="Pre-filled for entity_responses; empty for raw generation",
    )
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override for this entity"
    )


class UnifiedScenarioInput(BaseModel):
    """Scenario: entities, attributes, and optional pre-filled scenario_response.

    For raw_entities / entity_responses: scenario_response is empty; generation may fill it.
    For scenario_responses: scenario_response is pre-filled for summarization.
    """

    scenario_id: str = Field(..., description="Unique identifier for the scenario")
    entities: List[UnifiedEntityInput] = Field(
        ..., description="Entities in this scenario"
    )
    entity_count: int = Field(..., description="Number of entities in this scenario")
    scenario_attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Scenario-specific attributes"
    )
    scenario_response: Optional[str] = Field(
        None,
        description="Pre-filled for scenario_responses; empty for raw/entity generation",
    )
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override for this scenario"
    )


class UnifiedTicketInput(BaseModel):
    """Ticket within raw_entities when using tickets (ticket_raw_message)."""

    ticket_id: str = Field(..., description="Unique identifier for the ticket")
    ticket_attributes: Dict[str, Any] = Field(
        ...,
        description="Ticket context (ticket_id, sub_category_id, supplier_id, category_id, etc.)",
    )
    scenarios: List[UnifiedScenarioInput] = Field(
        ..., description="Scenarios with entities for this ticket"
    )
    scenario_count: int = Field(..., description="Number of scenarios in this ticket")
    template: Optional[RequestTemplate] = Field(
        None, description="Optional template override for this ticket"
    )


class ResponseGenerationData(BaseModel):
    """Unified input for all generation types: tickets -> scenarios -> entities.

    Expected shape is determined by generation_type.input_source: raw = generate from
    templates (entity_response/scenario_response empty); entity = summarize from
    pre-filled entity_response; scenario = summarize from pre-filled scenario_response.
    """

    tickets: List[UnifiedTicketInput] = Field(
        ...,
        description="Tickets with scenarios and entities; each has ticket_attributes",
    )
    template: Optional[RequestTemplate] = Field(
        None,
        description="Optional ticket/scenario-level template override",
    )


class UnifiedGenerateResponseRequest(BaseModel):
    """Unified request model for all generation types.

    Top-level `data` has tickets. generation_type (and its input_source: raw / entity /
    scenario) determines the expected input shape. Entity/scenario-level fields
    (entity_response, scenario_response) are optional; each generation type fills or
    consumes the needed ones.
    """

    generation_type: ResponseGenerationType = Field(
        ..., description="Type of generation to perform"
    )
    data: ResponseGenerationData = Field(
        ...,
        description="Input data (tickets -> scenarios -> entities); shape follows generation_type",
    )


class DispositionSCMappingItem(BaseModel):
    """Model for individual disposition SC mapping item."""

    l2_ss: str = Field(..., description="L2 SS value")
    sub_category_id: int = Field(..., description="Sub Category ID")


class DispositionSCBulkUpdateRequest(BaseModel):
    """Request model for bulk update of disposition SC mappings."""

    mappings: List[DispositionSCMappingItem] = Field(
        ..., description="List of mapping data from CSV"
    )


class DispositionSCSearchRequest(BaseModel):
    """Request model for searching disposition SC mappings."""

    l2_ss: Optional[str] = Field(None, description="L2 SS value to search for")
    sub_category_id: Optional[int] = Field(
        None, description="Sub Category ID to search for"
    )


class IntentDetectionExecuteRequest(BaseModel):
    """Request model for executing intent detection"""

    file_name: str = Field(..., description="Name of the file to process")
    ic_classifier_type: str = Field(..., description="Type of IC classifier to use")
    faq_classifier_type: str = Field(..., description="Type of FAQ classifier to use")


class IntentDetectionSummaryRequest(BaseModel):
    """Request model for getting intent detection summary"""

    file_name: str = Field(..., description="Name of the file to get summary for")


class ClassifyIntentRequest(BaseModel):
    ticket_description: str = Field(..., description="Ticket Description")
    supplier_sub_category_id: int = Field(
        ..., description="ID of the supplier sub-category"
    )
    ic_classifier_type: str = Field(..., description="Type of IC classifier to use")
    faq_classifier_type: str = Field(..., description="Type of FAQ classifier to use")


class EvaluateRequest(BaseModel):
    ticket_id: str = Field(..., description="Ticket ID")
    ticket_description: str = Field(..., description="Ticket Description")
    supplier_sub_category_id: int = Field(
        ..., description="ID of the supplier sub-category"
    )
    agent_selected_l2_disposition: str = Field(..., description="Agent Disposition")
    ic_classifier_type: str = Field(..., description="Type of IC classifier to use")
    faq_classifier_type: str = Field(..., description="Type of FAQ classifier to use")


class FaqDetectionRequest(BaseModel):
    supplier_id: Optional[int] = Field(None, description="Supplier ID")
    category_id: int = Field(..., description="Category ID")
    sub_category_id: int = Field(..., description="Sub-category ID")
    ticket_description: str = Field(..., description="Ticket description")
    faq_classification_id: str = Field(..., description="FAQ classification ID")
    faq_classification_flow_type: str = Field(
        ..., description="FAQ classification flow type"
    )


class CategoryMappingItem(BaseModel):
    """Model for individual category mapping item."""

    category_id: int = Field(alias="Category ID")
    category_title: str = Field(alias="Category Title")
    is_others: bool = Field(default=False, alias="Is Others")


class OldICSubcategoryMappingItem(BaseModel):
    """Model for individual old IC subcategory mapping item (without description)."""

    category_id: int = Field(alias="Category ID")
    sub_category_id: int = Field(alias="Sub Category ID")
    sub_category_title: str = Field(alias="Sub Category Title")
    is_others: bool = Field(default=False, alias="Is Others")


class ICSubcategoryMappingItem(BaseModel):
    """Model for individual IC subcategory mapping item."""

    category_id: int = Field(alias="Category ID")
    sub_category_id: int = Field(alias="Sub Category ID")
    sub_category_title: str = Field(alias="Sub Category Title")
    sub_category_description: str = Field(alias="Sub Category Description")
    is_others: bool = Field(default=False, alias="Is Others")


class IssueCategoryMappingItem(BaseModel):
    """Model for individual issue category mapping item."""

    category_id: int = Field(alias="Category ID")
    category_title: str = Field(alias="Category Title")
    category_description: str = Field(alias="Category Description")
    is_others: bool = Field(default=False, alias="Is Others")


class ResponseTemplateCreateRequest(BaseModel):
    """Request model for creating a response template."""

    sub_category_id: int = Field(..., description="Sub Category ID")
    scenario_identifier: str = Field(
        ..., description="Unique identifier for the scenario"
    )
    scenario_description: str = Field(..., description="Description of the scenario")
    response_template: str = Field(..., description="Template for generating responses")
    summary_template: str = Field(..., description="Template for generating summaries")
    links: Optional[Dict[str, Any]] = Field(
        None, description="Optional links associated with the template"
    )


class ResponseTemplateUpdateRequest(BaseModel):
    """Request model for updating a response template."""

    sub_category_id: Optional[int] = Field(None, description="Sub Category ID")
    scenario_identifier: Optional[str] = Field(
        None, description="Unique identifier for the scenario"
    )
    scenario_description: Optional[str] = Field(
        None, description="Description of the scenario"
    )
    response_template: Optional[str] = Field(
        None, description="Template for generating responses"
    )
    summary_template: Optional[str] = Field(
        None, description="Template for generating summaries"
    )
    links: Optional[Dict[str, Any]] = Field(
        None, description="Optional links associated with the template"
    )


class ResponseTemplateBulkUpdateRequest(BaseModel):
    """Request model for bulk update of response templates."""

    templates: List[ResponseTemplateCreateRequest] = Field(
        ..., description="List of template data from CSV"
    )


class ResponseTemplateSearchRequest(BaseModel):
    """Request model for searching response templates."""

    sub_category_id: Optional[int] = Field(
        None, description="Sub Category ID to search for"
    )
    scenario_identifier: Optional[str] = Field(
        None, description="Scenario identifier to search for"
    )
    scenario_description: Optional[str] = Field(
        None, description="Scenario description to search for"
    )


class ICAFAQGenerationRequest(BaseModel):
    """Request model for IC/FAQ generation."""

    texts: List[str] = Field(..., description="List of texts to process")
    initialize_from_existing: bool = Field(
        default=False,
        description="Whether to populate dictionary from existing IC/FAQ data",
    )
    ic_classifier_template_name: str = Field(
        ..., description="Name of the IC classifier template"
    )
    ic_classifier_template_namespace: str = Field(
        ..., description="Namespace of the IC classifier template"
    )
    ic_classifier_template_route_plan_name: str = Field(
        ..., description="Route plan name of the IC classifier template"
    )
    ic_classifier_template_temperature: float = Field(
        ..., description="Temperature for IC classifier"
    )
    faq_classifier_template_name: str = Field(
        ..., description="Name of the FAQ classifier template"
    )
    faq_classifier_template_namespace: str = Field(
        ..., description="Namespace of the FAQ classifier template"
    )
    faq_classifier_template_route_plan_name: str = Field(
        ..., description="Route plan name of the FAQ classifier template"
    )
    faq_classifier_template_temperature: float = Field(
        ..., description="Temperature for FAQ classifier"
    )
    request_id: str = Field(..., description="Request ID")


class ICAFAQGenerationCsvRequest(BaseModel):
    """Request to run IC/FAQ generation on a CSV file."""

    file_name: str = Field(
        ..., description="CSV file name in data/input (e.g. 'listening_tool.csv')"
    )
    batch_size: int = Field(
        default=50,
        description="Number of texts per generate_ic_faq_mappings call",
    )
    initialize_from_existing: bool = Field(
        default=False,
        description="Whether to seed the IC/FAQ dictionary from existing data on the first batch",
    )
