"""
Ticket resolution responses module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityResponse(BaseModel):
    """Model for individual response in the report."""

    entity_id: str = Field(..., description="Unique identifier for the entity")
    response: str = Field(..., description="The generated response text")


class ScenarioResponse(BaseModel):
    """Model for individual response in the report."""

    scenario_id: str = Field(..., description="Unique identifier for the scenario")
    response: Optional[str] = Field(None, description="The generated response text")
    entity_responses: List[EntityResponse] = Field(
        ..., description="List of entity responses"
    )


class GenerateResponseResponse(BaseModel):
    """Response model for generate-response endpoint (v1)."""

    summary: Optional[str] = Field(None, description="Overall response message")
    scenario_responses: Optional[List[ScenarioResponse]] = Field(
        None, description="List of scenario responses"
    )


class UnifiedEntityResponse(BaseModel):
    """Entity-level response for the unified v2 API.

    Aligns with RawEntityInput: entity_identifiers for correlation, response is the
    generated entity_response.
    """

    entity_identifiers: Dict[str, Any] = Field(
        ...,
        description="Same as request RawEntityInput.entity_identifiers for correlation",
    )
    response: str = Field(..., description="Generated response for this entity")


class UnifiedScenarioResponse(BaseModel):
    """Scenario-level response for the unified v2 API.

    Aligns with RawScenarioInput: scenario_id, entity_responses (matches entities),
    entity_count; scenario_response when generated at scenario level.
    """

    scenario_id: str = Field(..., description="Unique identifier for the scenario")
    scenario_response: Optional[str] = Field(
        None,
        description="Scenario-level response when generated (e.g. from entity summarization)",
    )
    entity_responses: List[UnifiedEntityResponse] = Field(
        ..., description="One response per entity, same order as request entities"
    )
    entity_count: int = Field(..., description="Number of entity responses")


class UnifiedTicketResponse(BaseModel):
    """Response for a single ticket in the unified v2 generate-response API.

    Mirrors the request's ticket structure: one entry per ticket.
    - Entity-level: scenario_responses is set (summary is None).
    - Ticket-level: summary is set (scenario_responses is None).
    """

    ticket_id: str = Field(..., description="Unique identifier for the ticket")
    summary: Optional[str] = Field(
        None, description="Ticket-level summary (for ticket-level generation)"
    )
    scenario_responses: Optional[List[UnifiedScenarioResponse]] = Field(
        None,
        description="Scenario and entity responses for this ticket (entity/scenario-level generation)",
    )


class UnifiedGenerateResponseResponse(BaseModel):
    """Unified v2 response model for generate-response: one TicketResponse per ticket in the request."""

    tickets: List[UnifiedTicketResponse] = Field(
        ...,
        description="One response per ticket, in the same order as the request",
    )


class IntentDetectionResponse(BaseModel):
    """Response model for intent detection execution request"""

    status: str = Field(description="Current status of the intent detection process")
    message: str = Field(description="Status message describing the current state")
    created_at: str = Field(
        description="ISO format timestamp when the process was created"
    )
    output_path: str = Field(description="Path to the output file containing results")


class ICSubcategoryMappingResponse(BaseModel):
    """Response model for IC subcategory mapping data."""

    id: str
    category_id: int
    sub_category_id: int
    sub_category_title: str
    sub_category_description: str
    is_others: bool
    created_at: str
    updated_at: str


class ICSubcategoryMappingListResponse(BaseModel):
    """Response model for list of IC subcategory mappings."""

    mappings: List[ICSubcategoryMappingResponse]
    total_count: int


class CategoryToSubcategoriesResponse(BaseModel):
    """Response model for category to subcategories mapping."""

    category_to_subcategories: Dict[int, List[int]]


class SubcategoryDetails(BaseModel):
    """Model for subcategory details."""

    category_id: int = Field(..., description="Category ID")
    sub_category_title: str = Field(..., description="Sub-category title")
    sub_category_description: str = Field(..., description="Sub-category description")
    is_others: bool = Field(..., description="Whether this is an 'Others' category")


class SubcategoryToDetailsResponse(BaseModel):
    """Response model for subcategory to details mapping."""

    subcategory_to_details: Dict[int, SubcategoryDetails]


class FAQItem(BaseModel):
    """Model for FAQ item in responses."""

    faq_id: str = Field(..., description="FAQ ID")
    faq_title: str = Field(..., description="FAQ title")
    issue_category_id: int = Field(..., description="Issue category ID")
    issue_category_title: str = Field(..., description="Issue category title")


class FaqDetectionResponse(BaseModel):
    label_text: str = Field(..., description="Label text")
    faq_classification_id: str = Field(..., description="FAQ classification ID")
    faq: List[FAQItem] = Field(..., description="FAQ")
    misc: Optional[Dict[str, Any]] = Field({}, description="Miscellaneous data")


class IssueCategoryClassificationResult(BaseModel):
    """Model for issue category classification result in responses."""

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


class FAQClassificationResult(BaseModel):
    """Model for FAQ classification result in responses."""

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


class IntentClassificationResponse(BaseModel):
    error_occurred: bool = Field(..., description="Whether an error occurred")
    error_code: Optional[int] = Field(None, description="Error code if error occurred")
    error_detail: Optional[str] = Field(
        None, description="Detailed error message if error occurred"
    )

    # Success fields (only populated when error_occurred=False)
    issue_category_result: Optional[IssueCategoryClassificationResult] = Field(
        None, description="Issue category classification result"
    )
    faq_result: Optional[FAQClassificationResult] = Field(
        None, description="FAQ/intent classification result"
    )


class IssueCategoryResponse(BaseModel):
    """Response model for issue category data."""

    id: str
    category_id: int
    category_title: str
    category_description: str
    is_others: bool
    created_at: str
    updated_at: str


class IssueCategoryInfo(BaseModel):
    """Model for issue category information."""

    title: str = Field(..., description="Category title")
    description: str = Field(..., description="Category description")


class IssueCategoryMappingResponse(BaseModel):
    """Response model for issue category mapping."""

    category_mapping: Dict[int, IssueCategoryInfo]


class IssueCategoryListResponse(BaseModel):
    """Response model for list of issue categories."""

    categories: List[IssueCategoryResponse]
    total_count: int


class IssueCategoryBulkUpdateResponse(BaseModel):
    """Response model for bulk update operations."""

    message: str
    created_count: int
    updated_count: int
    deleted_count: int
    total_processed: int
    errors: List[str]


class SubcategoryMappingResponse(BaseModel):
    """Response model for subcategory mapping data."""

    id: str
    category_id: int
    sub_category_id: int
    sub_category_title: str
    is_others: bool
    created_at: str
    updated_at: str


class SubcategoryMappingListResponse(BaseModel):
    """Response model for list of subcategory mappings."""

    mappings: List[SubcategoryMappingResponse]
    total_count: int


class CategoryResponse(BaseModel):
    """Response model for category data."""

    id: str
    category_id: int
    category_title: str
    is_others: bool
    created_at: str
    updated_at: str


class CategoryMappingResponse(BaseModel):
    """Response model for category mapping."""

    category_mapping: Dict[int, str]


class CategoryListResponse(BaseModel):
    """Response model for list of categories."""

    categories: List[CategoryResponse]
    total_count: int


class DispositionSCMappingResponse(BaseModel):
    """Response model for individual disposition SC mapping data."""

    l2_ss: str = Field(..., description="L2 SS value")
    sub_category_id: int = Field(..., description="Sub Category ID")
    created_at: Optional[str] = Field(
        None, description="Creation timestamp in ISO format"
    )
    updated_at: Optional[str] = Field(
        None, description="Last update timestamp in ISO format"
    )


class DispositionSCBulkUpdateResponse(BaseModel):
    """Response model for bulk update operation."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Operation result message")
    deleted_count: int = Field(..., description="Number of records deleted")
    inserted_count: int = Field(..., description="Number of records inserted")


class DispositionSCSearchResponse(BaseModel):
    """Response model for search operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    data: List[DispositionSCMappingResponse] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")


class DispositionSummaryResponse(BaseModel):
    """Response model for disposition service summary."""

    total_mappings: int = Field(..., description="Total number of mappings")
    unique_l2_ss: int = Field(..., description="Number of unique L2 SS values")
    unique_subcategories: int = Field(..., description="Number of unique subcategories")
    others_count: int = Field(..., description="Number of 'Others' categories")
    l2_ss_distribution: Dict[str, int] = Field(
        ..., description="L2 SS distribution (top 10)"
    )


class DispositionSCSummaryResponse(BaseModel):
    """Response model for summary statistics."""

    success: bool = Field(..., description="Whether the operation was successful")
    data: DispositionSummaryResponse = Field(..., description="Summary statistics")


class DispositionSCListResponse(BaseModel):
    """Response model for listing all mappings."""

    success: bool = Field(..., description="Whether the operation was successful")
    data: List[DispositionSCMappingResponse] = Field(..., description="All mappings")
    count: int = Field(..., description="Total number of mappings")


class BulkUpdateResponse(BaseModel):
    """Response model for bulk update operations."""

    message: str
    created_count: int
    updated_count: int
    deleted_count: int
    total_processed: int
    errors: List[str]


class SubcategoryDetailsItem(BaseModel):
    """Model for subcategory details item."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    sub_category_title: str = Field(..., description="Sub-category title")
    sub_category_description: str = Field(..., description="Sub-category description")
    is_others: bool = Field(..., description="Whether this is an 'Others' category")


class SubcategoriesForCategoryResponse(BaseModel):
    """Response model for getting subcategories for a specific category."""

    category_id: int = Field(..., description="Category ID")
    subcategory_count: int = Field(..., description="Number of subcategories")
    subcategories: List[SubcategoryDetailsItem] = Field(
        ..., description="List of subcategory details"
    )


class SubcategorySearchResult(BaseModel):
    """Model for subcategory search result."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    sub_category_title: str = Field(..., description="Sub-category title")
    sub_category_description: str = Field(..., description="Sub-category description")
    category_id: int = Field(..., description="Category ID")
    is_others: bool = Field(..., description="Whether this is an 'Others' category")


class SubcategorySearchResponse(BaseModel):
    """Response model for subcategory search operations."""

    search_term: str = Field(..., description="Search term used")
    total_results: int = Field(..., description="Total number of results")
    results: List[SubcategorySearchResult] = Field(..., description="Search results")


class CategoriesSummaryResponse(BaseModel):
    """Response model for categories summary."""

    total_categories: int = Field(..., description="Total number of categories")
    total_subcategories: int = Field(..., description="Total number of subcategories")
    others_categories_count: int = Field(
        ..., description="Number of 'Others' categories"
    )
    others_subcategories_count: int = Field(
        ..., description="Number of 'Others' subcategories"
    )


class CategorySummaryItem(BaseModel):
    """Model for individual category summary item."""

    subcategory_count: int = Field(
        ..., description="Number of subcategories in this category"
    )
    subcategory_ids: List[int] = Field(
        ..., description="List of subcategory IDs in this category"
    )


class DetailedCategoriesSummaryResponse(BaseModel):
    """Detailed response model for categories summary with category breakdown."""

    total_categories: int = Field(..., description="Total number of categories")
    total_subcategories: int = Field(..., description="Total number of subcategories")
    categories: Dict[int, CategorySummaryItem] = Field(
        ..., description="Breakdown by category"
    )


class OthersSubcategoriesResponse(BaseModel):
    """Response model for 'Others' subcategories."""

    others_subcategories: List[int] = Field(
        ..., description="List of 'Others' subcategory IDs"
    )
    count: int = Field(..., description="Number of 'Others' subcategories")


class OthersSubcategoriesForCategoryResponse(BaseModel):
    """Response model for 'Others' subcategories for a specific category."""

    category_id: int = Field(..., description="Category ID")
    others_subcategories: List[int] = Field(
        ..., description="List of 'Others' subcategory IDs for this category"
    )
    count: int = Field(
        ..., description="Number of 'Others' subcategories for this category"
    )


class SubcategoryOthersStatusResponse(BaseModel):
    """Response model for checking if a subcategory is marked as 'Others'."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    is_others: bool = Field(
        ..., description="Whether this subcategory is marked as 'Others'"
    )


class ClearAllResponse(BaseModel):
    """Response model for clearing all mappings."""

    message: str = Field(..., description="Operation result message")


class IntentMetrics(BaseModel):
    """Model for intent detection metrics."""

    agent_model_match_true: int = Field(..., description="Number of true matches")
    agent_model_match_false: int = Field(..., description="Number of false matches")
    agent_model_match_nan: int = Field(..., description="Number of NaN matches")
    match_rate: float = Field(..., description="Match rate percentage")


class ScenarioMetrics(BaseModel):
    """Model for IC/FAQ scenario-specific metrics."""

    total_cases: int = Field(..., description="Total number of cases in this scenario")
    successful_cases: int = Field(
        ..., description="Number of successful cases in this scenario"
    )
    error_cases: Dict[str, int] = Field(
        ..., description="Error cases by error code for this scenario"
    )
    success_rate: float = Field(
        ..., description="Success rate percentage for this scenario"
    )
    error_rate: float = Field(
        ..., description="Error rate percentage for this scenario"
    )
    single_intent: IntentMetrics = Field(
        ..., description="Single intent metrics for this scenario"
    )
    multiple_intent: IntentMetrics = Field(
        ..., description="Multiple intent metrics for this scenario"
    )
    overall_metrics: IntentMetrics = Field(
        ..., description="Overall metrics for this scenario"
    )
    average_stats: Optional["AverageStats"] = Field(
        None, description="Average statistics for this scenario"
    )


class AverageStats(BaseModel):
    """Model for average statistics across all cases."""

    avg_confidence_score: float = Field(
        ..., description="Average confidence score across all successful cases"
    )
    avg_latency: float = Field(
        ..., description="Average latency across all successful cases"
    )
    avg_input_tokens: float = Field(
        ..., description="Average input tokens across all successful cases"
    )
    avg_output_tokens: float = Field(
        ..., description="Average output tokens across all successful cases"
    )
    avg_total_tokens: float = Field(
        ..., description="Average total tokens across all successful cases"
    )
    total_invocations: int = Field(..., description="Total number of LLM invocations")
    total_successful_invocations: int = Field(
        ..., description="Total number of successful LLM invocations"
    )
    total_failed_invocations: int = Field(
        ..., description="Total number of failed LLM invocations"
    )
    invocation_success_rate: float = Field(
        ..., description="Success rate of LLM invocations"
    )


# Rebuild ScenarioMetrics to resolve forward reference to AverageStats
ScenarioMetrics.model_rebuild()


class IntentDetectionSummaryResponse(BaseModel):
    """Response model for intent detection summary."""

    total_cases: int = Field(..., description="Total number of cases")
    successful_cases: int = Field(..., description="Number of successful cases")
    error_cases: Dict[str, int] = Field(..., description="Error cases by error code")
    success_rate: float = Field(..., description="Success rate percentage")
    error_rate: float = Field(..., description="Error rate percentage")
    single_intent: IntentMetrics = Field(..., description="Single intent metrics")
    multiple_intent: IntentMetrics = Field(..., description="Multiple intent metrics")
    overall_metrics: IntentMetrics = Field(..., description="Overall metrics")
    # New fields for bifurcation and average stats
    scenario_breakdown: Dict[str, ScenarioMetrics] = Field(
        ..., description="Breakdown by IC/FAQ scenario"
    )
    average_stats: AverageStats = Field(
        ..., description="Average statistics across all cases"
    )


class IntentDetectionExecuteResponse(BaseModel):
    """Response model for intent detection execution."""

    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Status message")
    file_name: str = Field(..., description="Processed file name")
    output_path: str = Field(..., description="Output file path")
    created_at: str = Field(..., description="Creation timestamp")


class OldIssueCategoryResponse(BaseModel):
    """Response model for old issue category data."""

    id: str
    category_id: int
    category_title: str
    is_others: bool
    created_at: str
    updated_at: str


class OldIssueCategoryListResponse(BaseModel):
    """Response model for list of old issue categories."""

    categories: List[OldIssueCategoryResponse]
    total_count: int


class OldICSubcategoryMappingResponse(BaseModel):
    """Response model for old IC subcategory mapping data."""

    id: str
    category_id: int
    sub_category_id: int
    sub_category_title: str
    is_others: bool
    created_at: str
    updated_at: str


class OldICSubcategoryMappingListResponse(BaseModel):
    """Response model for list of old IC subcategory mappings."""

    mappings: List[OldICSubcategoryMappingResponse]
    total_count: int


class OldSubcategorySearchResult(BaseModel):
    """Model for old subcategory search result."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    sub_category_title: str = Field(..., description="Sub-category title")
    category_id: int = Field(..., description="Category ID")
    is_others: bool = Field(..., description="Whether this is an 'Others' category")


class OldSubcategorySearchResponse(BaseModel):
    """Response model for old subcategory search operations."""

    search_term: str = Field(..., description="Search term used")
    results: List[OldSubcategorySearchResult] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")


class OldCategoriesSummaryResponse(BaseModel):
    """Response model for old categories summary."""

    total_categories: int = Field(..., description="Total number of categories")
    total_subcategories: int = Field(..., description="Total number of subcategories")
    categories: Dict[int, CategorySummaryItem] = Field(
        ..., description="Breakdown by category"
    )


class OldOthersSubcategoryItem(BaseModel):
    """Model for old 'Others' subcategory item."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    sub_category_title: str = Field(..., description="Sub-category title")
    category_id: int = Field(..., description="Category ID")


class OldOthersSubcategoriesResponse(BaseModel):
    """Response model for old 'Others' subcategories."""

    others_subcategories: List[OldOthersSubcategoryItem] = Field(
        ..., description="List of 'Others' subcategories"
    )
    count: int = Field(..., description="Number of 'Others' subcategories")


class OldOthersSubcategoriesForCategoryItem(BaseModel):
    """Model for old 'Others' subcategory item for specific category."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    sub_category_title: str = Field(..., description="Sub-category title")


class OldOthersSubcategoriesForCategoryResponse(BaseModel):
    """Response model for old 'Others' subcategories for a specific category."""

    category_id: int = Field(..., description="Category ID")
    others_subcategories: List[OldOthersSubcategoryItem] = Field(
        ..., description="List of 'Others' subcategories for this category"
    )
    count: int = Field(
        ..., description="Number of 'Others' subcategories for this category"
    )


class OldSubcategoryOthersStatusResponse(BaseModel):
    """Response model for checking if an old subcategory is marked as 'Others'."""

    sub_category_id: int = Field(..., description="Sub-category ID")
    is_others: bool = Field(
        ..., description="Whether this subcategory is marked as 'Others'"
    )
    sub_category_title: Optional[str] = Field(None, description="Sub-category title")
    sub_category_description: Optional[str] = Field(
        None, description="Sub-category description"
    )
    category_id: Optional[int] = Field(None, description="Category ID")


class OldBulkUpdateResponse(BaseModel):
    """Response model for old bulk update operations."""

    success_count: int = Field(
        ..., description="Number of successfully updated mappings"
    )
    error_count: int = Field(..., description="Number of failed updates")
    errors: List[str] = Field(..., description="List of error messages")
    total_processed: int = Field(..., description="Total number of mappings processed")


class ResponseTemplateResponse(BaseModel):
    """Response model for response template data."""

    id: str
    sub_category_id: int
    scenario_identifier: str
    scenario_description: str
    response_template: str
    summary_template: str
    links: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class ResponseTemplateListResponse(BaseModel):
    """Response model for list of response templates."""

    templates: List[ResponseTemplateResponse]
    total_count: int


class ResponseTemplateBulkUpdateResponse(BaseModel):
    """Response model for bulk update operations on response templates."""

    message: str
    created_count: int
    updated_count: int
    deleted_count: int
    total_processed: int


class ResponseTemplateSearchResponse(BaseModel):
    """Response model for response template search results."""

    templates: List[ResponseTemplateResponse]
    total_count: int
    search_criteria: Dict[str, Any]


class ICAFAQResult(BaseModel):
    """Result model for a single text's IC/FAQ mapping."""

    text: str = Field(..., description="Input text")
    ic_id: int = Field(..., description="Selected or suggested IC ID")
    ic_title: str = Field(..., description="IC title")
    ic_description: str = Field(..., description="IC description")
    faq_id: int = Field(..., description="Selected or suggested FAQ ID")
    faq_title: str = Field(..., description="FAQ title")
    faq_description: str = Field(..., description="FAQ description")
    is_new_ic: bool = Field(..., description="Whether this IC was newly suggested")
    is_new_faq: bool = Field(..., description="Whether this FAQ was newly suggested")
    error_occurred: bool = Field(
        default=False, description="Whether an error occurred during processing"
    )
    error_detail: Optional[str] = Field(
        None, description="Error detail if error occurred"
    )


class ICAFAQGenerationResponse(BaseModel):
    """Response model for IC/FAQ generation."""

    results: List[ICAFAQResult] = Field(
        ..., description="List of results for each input text"
    )
    final_ic_dictionary: Dict[int, Dict[str, Any]] = Field(
        ..., description="Final nested dictionary structure of ICs and FAQs"
    )
    total_ics: int = Field(..., description="Total number of ICs in final dictionary")
    total_faqs: int = Field(..., description="Total number of FAQs in final dictionary")


class ICAFAQGenerationCsvResponse(BaseModel):
    """Response model for IC/FAQ generation CSV process."""

    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Status message")
    file_name: str = Field(..., description="Processed file name")
    output_path: str = Field(..., description="Output CSV path")
    final_ic_dictionary: Dict[str, Any] = Field(
        ...,
        description="All ICs and their FAQs as JSON: { ic_id: { title, description, faqs: { faq_id: { title, description } } } }",
    )
