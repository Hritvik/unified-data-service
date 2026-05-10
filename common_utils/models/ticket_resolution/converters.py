"""
Converters for ticket resolution models.

This module provides conversion functions between different model types
used in the ticket resolution system.
"""

from typing import Any, Dict, Optional

from common_utils.constants import ErrorCodes
from common_utils.enums import OutputSchemaName
from common_utils.models.ticket_resolution.entities import (
    EvaluationClassifierOutput,
    FAQResult,
    IntentClassificationResult,
    IssueCategoryResult,
    ProductionClassifierOutput,
    SimpleAgentOutput,
)
from common_utils.models.ticket_resolution.responses import (
    FAQClassificationResult,
    IntentClassificationResponse,
    IssueCategoryClassificationResult,
)


def _extract_reasoning_steps(classifier_output: SimpleAgentOutput) -> Dict[str, Any]:
    """
    Safely extract reasoning steps from classifier output.

    Args:
        classifier_output: The classifier output to extract from

    Returns:
        Dictionary containing reasoning steps or empty dict if not available
    """
    reasoning_steps: Dict[str, Any] = {}

    if (
        hasattr(classifier_output, "reasoning_steps")
        and classifier_output.reasoning_steps
    ):
        try:
            # Handle both EvaluationClassifierOutput and ProductionClassifierOutput reasoning steps
            if hasattr(classifier_output.reasoning_steps, "input_assessment"):
                reasoning_steps[
                    "input_assessment"
                ] = classifier_output.reasoning_steps.input_assessment
            if hasattr(classifier_output.reasoning_steps, "decision_rationale"):
                reasoning_steps[
                    "decision_rationale"
                ] = classifier_output.reasoning_steps.decision_rationale
            if hasattr(classifier_output.reasoning_steps, "output_rationale"):
                reasoning_steps[
                    "output_rationale"
                ] = classifier_output.reasoning_steps.output_rationale
        except Exception:
            # If any extraction fails, return empty dict
            reasoning_steps = {}

    return reasoning_steps


def _extract_metadata(classifier_output: SimpleAgentOutput) -> Dict[str, Any]:
    """
    Safely extract metadata from classifier output.

    Args:
        classifier_output: The classifier output to extract from

    Returns:
        Dictionary containing metadata or empty dict if not available
    """
    metadata: Dict[str, Any] = {}

    if hasattr(classifier_output, "metadata") and classifier_output.metadata:
        try:
            # Handle different metadata types
            if hasattr(classifier_output.metadata, "redundant_ticket_description"):
                # ClassificationMetadata
                metadata.update(
                    {
                        "redundant_ticket_description": classifier_output.metadata.redundant_ticket_description,
                        "input_quality_score": classifier_output.metadata.input_quality_score,
                        "ambiguity_level": classifier_output.metadata.ambiguity_level,
                        "key_themes_identified": classifier_output.metadata.key_themes_identified,
                        "viable_options": classifier_output.metadata.viable_options,
                    }
                )
            elif hasattr(classifier_output.metadata, "output_script"):
                # ResponseGenerationMetadata
                metadata.update(
                    {
                        "output_script": classifier_output.metadata.output_script,
                        "output_language": classifier_output.metadata.output_language,
                    }
                )
        except Exception:
            # If any extraction fails, return empty dict
            metadata = {}

    # Add parent class fields
    if classifier_output.output_schema_name:
        metadata["output_schema_name"] = classifier_output.output_schema_name.value

    return metadata


def _validate_confidence_score(confidence_score: float, threshold: float = 0.5) -> bool:
    """
    Validate if confidence score meets the threshold.

    Args:
        confidence_score: The confidence score to validate
        threshold: Minimum threshold (default 0.5)

    Returns:
        True if score meets threshold, False otherwise
    """
    return confidence_score >= threshold


def _extract_classification_id(classifier_output: SimpleAgentOutput) -> Optional[int]:
    """
    Safely extract the first classification ID from classifier output.

    Args:
        classifier_output: The classifier output to extract from

    Returns:
        First classification ID or None if not available
    """
    if (
        hasattr(classifier_output, "success_details")
        and classifier_output.success_details
        and classifier_output.success_details.classification
    ):
        try:
            return classifier_output.success_details.classification[0]
        except (IndexError, AttributeError):
            return None
    return None


def convert_evaluation_classifier_to_issue_category_result(
    classifier_output: EvaluationClassifierOutput, confidence_threshold: float = 0.5
) -> IssueCategoryResult:
    """
    Convert EvaluationClassifierOutput to IssueCategoryResult.

    Args:
        classifier_output: The evaluation classifier output to convert
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        IssueCategoryResult with converted data
    """
    if not classifier_output.success or not classifier_output.success_details:
        return _handle_classifier_failure_to_issue_category_result(classifier_output)

    success_details = classifier_output.success_details
    confidence_score = success_details.confidence_score

    # Validate confidence score
    if not _validate_confidence_score(confidence_score, confidence_threshold):
        return IssueCategoryResult(
            error_occurred=True,
            error_code=ErrorCodes.IC_CLASSIFICATION_LOW_CONFIDENCE,
            error_detail="IC Detection Fail: Low Confidence Score",
            detected_issue_category_ids=None,
            detected_issue_category_confidence_score=confidence_score,
            detected_issue_category_reasoning_steps={},
            detected_issue_category_metadata={},
            invocation_journey=classifier_output.invocation_journey or [],
            invocation_summary=classifier_output.invocation_summary,
        )

    # Extract issue category IDs - support both single and multiple classifications
    issue_category_ids = (
        success_details.classification if success_details.classification else []
    )

    if not issue_category_ids:
        return IssueCategoryResult(
            error_occurred=True,
            error_code=ErrorCodes.IC_CLASSIFICATION_NO_MATCH_FOUND,
            error_detail="IC Detection Fail: Empty Issue Category Array",
            detected_issue_category_ids=None,
            detected_issue_category_confidence_score=confidence_score,
            detected_issue_category_reasoning_steps={},
            detected_issue_category_metadata={},
            invocation_journey=classifier_output.invocation_journey or [],
            invocation_summary=classifier_output.invocation_summary,
        )

    # Extract reasoning steps and metadata
    reasoning_steps = _extract_reasoning_steps(classifier_output)
    metadata = _extract_metadata(classifier_output)

    return IssueCategoryResult(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        detected_issue_category_ids=issue_category_ids,
        detected_issue_category_confidence_score=confidence_score,
        detected_issue_category_reasoning_steps=reasoning_steps,
        detected_issue_category_metadata=metadata,
        invocation_journey=classifier_output.invocation_journey or [],
        invocation_summary=classifier_output.invocation_summary,
    )


def convert_evaluation_classifier_to_faq_result(
    classifier_output: EvaluationClassifierOutput,
    confidence_threshold: float = 0.5,
) -> FAQResult:
    """
    Convert EvaluationClassifierOutput to FAQResult.

    Args:
        classifier_output: The evaluation classifier output to convert
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        FAQResult with converted data
    """
    if not classifier_output.success:
        return FAQResult(
            error_occurred=True,
            error_code=classifier_output.failure_details.error_code
            if classifier_output.failure_details
            else None,
            error_detail="Classification failed",
        )

    if not classifier_output.success_details:
        return FAQResult(
            error_occurred=True,
            error_code=-1,
            error_detail="No success details available",
        )

    # Validate confidence score
    confidence_score = classifier_output.success_details.confidence_score
    if not _validate_confidence_score(confidence_score, confidence_threshold):
        return FAQResult(
            error_occurred=True,
            error_code=-1,
            error_detail=f"Low confidence score: {confidence_score} (threshold: {confidence_threshold})",
        )

    # Extract reasoning steps and metadata
    reasoning_steps = _extract_reasoning_steps(classifier_output)
    metadata = _extract_metadata(classifier_output)

    return FAQResult(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        detected_intent=classifier_output.success_details.classification,
        detected_intent_confidence_score=confidence_score,
        detected_intent_reasoning_steps=reasoning_steps,
        detected_intent_metadata=metadata,
        invocation_journey=classifier_output.invocation_journey,
        invocation_summary=classifier_output.invocation_summary,
    )


def convert_production_classifier_to_issue_category_result(
    classifier_output: ProductionClassifierOutput, confidence_threshold: float = 0.5
) -> IssueCategoryResult:
    """
    Convert ProductionClassifierOutput to IssueCategoryResult.

    Args:
        classifier_output: The production classifier output to convert
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        IssueCategoryResult with converted data
    """
    if not classifier_output.success or not classifier_output.success_details:
        return _handle_classifier_failure_to_issue_category_result(classifier_output)

    success_details = classifier_output.success_details
    confidence_score = success_details.confidence_score

    # Validate confidence score
    if not _validate_confidence_score(confidence_score, confidence_threshold):
        return IssueCategoryResult(
            error_occurred=True,
            error_code=ErrorCodes.IC_CLASSIFICATION_LOW_CONFIDENCE,
            error_detail="IC Detection Fail: Low Confidence Score",
            detected_issue_category_ids=None,
            detected_issue_category_confidence_score=confidence_score,
            detected_issue_category_reasoning_steps={},
            detected_issue_category_metadata={},
            invocation_journey=classifier_output.invocation_journey or [],
            invocation_summary=classifier_output.invocation_summary,
        )

    # Extract issue category IDs - support both single and multiple classifications
    issue_category_ids = (
        success_details.classification if success_details.classification else []
    )

    if not issue_category_ids:
        return IssueCategoryResult(
            error_occurred=True,
            error_code=ErrorCodes.IC_CLASSIFICATION_NO_MATCH_FOUND,
            error_detail="IC Detection Fail: Empty Issue Category Array",
            detected_issue_category_ids=None,
            detected_issue_category_confidence_score=confidence_score,
            detected_issue_category_reasoning_steps={},
            detected_issue_category_metadata={},
            invocation_journey=classifier_output.invocation_journey or [],
            invocation_summary=classifier_output.invocation_summary,
        )

    # Extract reasoning steps and metadata (ProductionClassifierOutput doesn't have these)
    reasoning_steps = {}
    metadata = _extract_metadata(classifier_output)

    return IssueCategoryResult(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        detected_issue_category_ids=issue_category_ids,
        detected_issue_category_confidence_score=confidence_score,
        detected_issue_category_reasoning_steps=reasoning_steps,
        detected_issue_category_metadata=metadata,
        invocation_journey=classifier_output.invocation_journey or [],
        invocation_summary=classifier_output.invocation_summary,
    )


def convert_production_classifier_to_faq_result(
    classifier_output: ProductionClassifierOutput,
    confidence_threshold: float = 0.5,
) -> FAQResult:
    """
    Convert ProductionClassifierOutput to FAQResult.

    Args:
        classifier_output: The production classifier output to convert
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        FAQResult with converted data
    """
    if not classifier_output.success:
        return FAQResult(
            error_occurred=True,
            error_code=classifier_output.failure_details.error_code
            if classifier_output.failure_details
            else None,
            error_detail="Classification failed",
        )

    if not classifier_output.success_details:
        return FAQResult(
            error_occurred=True,
            error_code=-1,
            error_detail="No success details available",
        )

    # Validate confidence score
    confidence_score = classifier_output.success_details.confidence_score
    if not _validate_confidence_score(confidence_score, confidence_threshold):
        return FAQResult(
            error_occurred=True,
            error_code=-1,
            error_detail=f"Low confidence score: {confidence_score} (threshold: {confidence_threshold})",
        )

    # Extract reasoning steps and metadata (production classifiers have limited fields)
    reasoning_steps = _extract_reasoning_steps(classifier_output)
    metadata = _extract_metadata(classifier_output)

    return FAQResult(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        detected_intent=classifier_output.success_details.classification,
        detected_intent_confidence_score=confidence_score,
        detected_intent_reasoning_steps=reasoning_steps,
        detected_intent_metadata=metadata,
        invocation_journey=classifier_output.invocation_journey,
        invocation_summary=classifier_output.invocation_summary,
    )


def auto_convert_to_issue_category_result(
    classifier_output: SimpleAgentOutput, confidence_threshold: float = 0.5
) -> IssueCategoryResult:
    """
    Automatically convert SimpleAgentOutput to IssueCategoryResult based on output_schema_name.

    This method determines which converter to use based on the output_schema_name field
    and delegates to the appropriate converter function.

    Args:
        classifier_output: The classifier output to convert (must have output_schema_name set)
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        IssueCategoryResult with converted data

    Raises:
        ValueError: If output_schema_name is not set or is not a supported classifier type
    """
    if not classifier_output.output_schema_name:
        raise ValueError("output_schema_name must be set for auto-conversion")

    # Handle failure cases first
    if not classifier_output.success:
        return _handle_classifier_failure_to_issue_category_result(classifier_output)

    # Handle success cases based on output_schema_name
    if classifier_output.output_schema_name == OutputSchemaName.EVALUATION_CLASSIFIER:
        return convert_evaluation_classifier_to_issue_category_result(
            classifier_output, confidence_threshold
        )
    elif classifier_output.output_schema_name == OutputSchemaName.PRODUCTION_CLASSIFIER:
        return convert_production_classifier_to_issue_category_result(
            classifier_output, confidence_threshold
        )
    else:
        raise ValueError(
            f"Unsupported classifier type: {classifier_output.output_schema_name}"
        )


def auto_convert_to_faq_result(
    classifier_output: SimpleAgentOutput, confidence_threshold: float = 0.5
) -> FAQResult:
    """
    Automatically convert SimpleAgentOutput to FAQResult based on output_schema_name.

    This method determines which converter to use based on the output_schema_name field
    and delegates to the appropriate converter function.

    Args:
        classifier_output: The classifier output to convert (must have output_schema_name set)
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        FAQResult with converted data

    Raises:
        ValueError: If output_schema_name is not set or is not a supported classifier type
    """
    if not classifier_output.output_schema_name:
        raise ValueError("output_schema_name must be set for auto-conversion")

    # Handle failure cases first
    if not classifier_output.success:
        return _handle_classifier_failure_to_faq_result(classifier_output)

    # Handle success cases based on output_schema_name
    if classifier_output.output_schema_name == OutputSchemaName.EVALUATION_CLASSIFIER:
        return convert_evaluation_classifier_to_faq_result(
            classifier_output, confidence_threshold
        )
    elif classifier_output.output_schema_name == OutputSchemaName.PRODUCTION_CLASSIFIER:
        return convert_production_classifier_to_faq_result(
            classifier_output, confidence_threshold
        )
    else:
        raise ValueError(
            f"Unsupported classifier type: {classifier_output.output_schema_name}"
        )


def _handle_classifier_failure_to_issue_category_result(
    classifier_output: SimpleAgentOutput,
) -> IssueCategoryResult:
    """
    Handle classifier failure cases and convert to IssueCategoryResult with appropriate error details.

    Args:
        classifier_output: The failed classifier output

    Returns:
        IssueCategoryResult with error details
    """
    if not classifier_output.failure_details:
        return IssueCategoryResult(
            error_occurred=True,
            error_code=ErrorCodes.SYSTEM_ERROR,
            error_detail="Classification failed with unknown error",
            detected_issue_category_ids=None,
            detected_issue_category_confidence_score=0.0,
            detected_issue_category_reasoning_steps={},
            detected_issue_category_metadata={},
            invocation_journey=classifier_output.invocation_journey or [],
            invocation_summary=classifier_output.invocation_summary,
        )

    failure_details = classifier_output.failure_details
    llm_error_code = failure_details.error_code or ErrorCodes.SYSTEM_ERROR

    # Map generic LLM error codes to specific IC classification error codes
    if llm_error_code == ErrorCodes.LLM_FOUND_INSUFFICIENT_CONTEXT:
        error_code = ErrorCodes.IC_CLASSIFICATION_INSUFFICIENT_CONTEXT_ERROR
        error_detail = "IC Detection Fail: Insufficient Context"
    elif llm_error_code == ErrorCodes.LLM_FOUND_NO_MATCH:
        error_code = ErrorCodes.IC_CLASSIFICATION_NO_MATCH_FOUND
        error_detail = "IC Detection Fail: No Match Found"
    elif llm_error_code == ErrorCodes.CMB_DETECTED:
        error_code = ErrorCodes.CMB_DETECTED
        error_detail = "IC Detection Fail: CMB Detected"
    else:
        error_code = ErrorCodes.SYSTEM_ERROR
        error_detail = f"IC Detection Fail: Unknown Error (LLM Code: {llm_error_code})"

    return IssueCategoryResult(
        error_occurred=True,
        error_code=error_code,
        error_detail=error_detail,
        detected_issue_category_ids=None,
        detected_issue_category_confidence_score=0.0,
        detected_issue_category_reasoning_steps={},
        detected_issue_category_metadata={},
        invocation_journey=classifier_output.invocation_journey or [],
        invocation_summary=classifier_output.invocation_summary,
    )


def _handle_classifier_failure_to_faq_result(
    classifier_output: SimpleAgentOutput,
) -> FAQResult:
    """
    Handle classifier failure cases and convert to FAQResult with appropriate error details.

    Args:
        classifier_output: The failed classifier output

    Returns:
        FAQResult with error details
    """
    from common_utils.constants import ErrorCodes

    if not classifier_output.failure_details:
        return FAQResult(
            error_occurred=True,
            error_code=ErrorCodes.SYSTEM_ERROR,
            error_detail="Classification failed with unknown error",
            detected_intent=None,
            detected_intent_confidence_score=0.0,
            detected_intent_reasoning_steps={},
            detected_intent_metadata={},
            invocation_journey=classifier_output.invocation_journey or [],
            invocation_summary=classifier_output.invocation_summary,
        )

    failure_details = classifier_output.failure_details
    llm_error_code = failure_details.error_code or ErrorCodes.SYSTEM_ERROR

    # Map generic LLM error codes to specific FAQ classification error codes
    if llm_error_code == ErrorCodes.LLM_FOUND_INSUFFICIENT_CONTEXT:
        error_code = ErrorCodes.FAQ_CLASSIFICATION_INSUFFICIENT_CONTEXT_ERROR
        error_detail = "FAQ Detection Fail: Insufficient Context"
    elif llm_error_code == ErrorCodes.LLM_FOUND_NO_MATCH:
        error_code = ErrorCodes.FAQ_CLASSIFICATION_NO_MATCH_FOUND
        error_detail = "FAQ Detection Fail: No Match Found"
    else:
        error_code = ErrorCodes.SYSTEM_ERROR
        error_detail = f"FAQ Detection Fail: Unknown Error (LLM Code: {llm_error_code})"

    return FAQResult(
        error_occurred=True,
        error_code=error_code,
        error_detail=error_detail,
        detected_intent=None,
        detected_intent_confidence_score=0.0,
        detected_intent_reasoning_steps={},
        detected_intent_metadata={},
        invocation_journey=classifier_output.invocation_journey or [],
        invocation_summary=classifier_output.invocation_summary,
    )


def auto_convert_classifier_output(
    classifier_output: SimpleAgentOutput,
    confidence_threshold: float = 0.5,
) -> tuple[IssueCategoryResult, FAQResult]:
    """
    Automatically convert SimpleAgentOutput to both IssueCategoryResult and FAQResult.

    This method determines which converter to use based on the output_schema_name field
    and returns both converted results. This is useful when you need both issue category
    and FAQ results from the same classifier output.

    Args:
        classifier_output: The classifier output to convert (must have output_schema_name set)
        confidence_threshold: Minimum confidence score threshold (default 0.5)

    Returns:
        Tuple of (IssueCategoryResult, FAQResult) with converted data

    Raises:
        ValueError: If output_schema_name is not set or is not a supported classifier type
    """
    ic_result = auto_convert_to_issue_category_result(
        classifier_output, confidence_threshold
    )
    faq_result = auto_convert_to_faq_result(classifier_output, confidence_threshold)
    return ic_result, faq_result


def convert_issue_category_result_to_classification_result(
    issue_category_result: IssueCategoryResult,
) -> IssueCategoryClassificationResult:
    """
    Convert IssueCategoryResult to IssueCategoryClassificationResult.

    This function converts the internal IssueCategoryResult model to the response
    model IssueCategoryClassificationResult used in API responses.

    Args:
        issue_category_result: The IssueCategoryResult to convert

    Returns:
        IssueCategoryClassificationResult with converted data
    """

    if issue_category_result.error_occurred:
        return IssueCategoryClassificationResult(
            error_occurred=True,
            error_code=issue_category_result.error_code,
            error_detail=issue_category_result.error_detail,
            detected_issue_category_ids=None,
            detected_issue_category_confidence_score=None,
        )

    return IssueCategoryClassificationResult(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        detected_issue_category_ids=issue_category_result.detected_issue_category_ids,
        detected_issue_category_confidence_score=issue_category_result.detected_issue_category_confidence_score,
    )


def convert_faq_result_to_classification_result(
    faq_result: FAQResult,
) -> FAQClassificationResult:
    """
    Convert FAQResult to FAQClassificationResult.

    This function converts the internal FAQResult model to the response
    model FAQClassificationResult used in API responses.

    Args:
        faq_result: The FAQResult to convert

    Returns:
        FAQClassificationResult with converted data
    """

    if faq_result.error_occurred:
        return FAQClassificationResult(
            error_occurred=True,
            error_code=faq_result.error_code,
            error_detail=faq_result.error_detail,
            detected_intent=None,
            detected_intent_confidence_score=None,
        )

    return FAQClassificationResult(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        detected_intent=faq_result.detected_intent,
        detected_intent_confidence_score=faq_result.detected_intent_confidence_score,
    )


def convert_intent_classification_result_to_response(
    intent_classification_result: IntentClassificationResult,
) -> IntentClassificationResponse:
    """
    Convert IntentClassificationResult to IntentClassificationResponse.

    This function converts the internal IntentClassificationResult model to the response
    model IntentClassificationResponse used in API responses.

    Args:
        intent_classification_result: The IntentClassificationResult to convert

    Returns:
        IntentClassificationResponse with converted data
    """

    if intent_classification_result.error_occurred:
        return IntentClassificationResponse(
            error_occurred=True,
            error_code=intent_classification_result.error_code,
            error_detail=intent_classification_result.error_detail,
            issue_category_result=None,
            faq_result=None,
        )

    # Convert internal models to response models
    issue_category_response = None
    if intent_classification_result.issue_category_result:
        issue_category_response = (
            convert_issue_category_result_to_classification_result(
                intent_classification_result.issue_category_result
            )
        )

    faq_response = None
    if intent_classification_result.faq_result:
        faq_response = convert_faq_result_to_classification_result(
            intent_classification_result.faq_result
        )

    return IntentClassificationResponse(
        error_occurred=False,
        error_code=None,
        error_detail=None,
        issue_category_result=issue_category_response,
        faq_result=faq_response,
    )
