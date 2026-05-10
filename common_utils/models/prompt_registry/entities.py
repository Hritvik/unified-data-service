"""
Prompt registry entities module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from typing import Dict, List

from pydantic import BaseModel, Field


class PromptTemplateData(BaseModel):
    """Type definition for prompt template data returned by services."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Name of the template")
    template: str = Field(..., description="The prompt template content")
    prompt_input: str = Field(..., description="Input for the prompt template")
    namespace: str = Field(..., description="Namespace for organizing templates")
    components: List[str] = Field(
        default_factory=list, description="List of component references"
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class PromptComponentData(BaseModel):
    """Type definition for prompt component data returned by services."""

    id: str = Field(..., description="Unique identifier")
    component_name: str = Field(..., description="Name of the component")
    component_type: str = Field(..., description="Type/category of the component")
    content: str = Field(..., description="The component content")
    namespace: str = Field(..., description="Namespace for organizing components")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class ResolvedComponentData(BaseModel):
    """Type definition for resolved component data."""

    component_name: str = Field(..., description="Name of the component")
    component_type: str = Field(..., description="Type of the component")
    content: str = Field(..., description="Resolved content of the component")
    namespace: str = Field(..., description="Namespace of the component")


class ResolvedTemplateData(BaseModel):
    """Type definition for resolved template data."""

    resolved_template: str = Field(
        ..., description="The template with all components resolved"
    )
    original_template: str = Field(
        ..., description="The original template with placeholders"
    )
    template_name: str = Field(..., description="Name of the template")
    template_namespace: str = Field(..., description="Namespace of the template")
    resolved_components: Dict[str, ResolvedComponentData] = Field(
        default_factory=dict,
        description="Dictionary of resolved components by reference",
    )
    components_used: List[str] = Field(
        default_factory=list, description="List of component references used"
    )


class TemplateResolutionOutput(BaseModel):
    """Type definition for combined template resolution and input prompt formatting output."""

    resolved_template: str = Field(
        ..., description="The template with all components resolved"
    )
    input_prompt: str = Field(
        ..., description="The formatted input prompt with kwargs applied"
    )
