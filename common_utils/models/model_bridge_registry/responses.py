"""
Model bridge registry responses module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common_utils.enums import (
    APIContract,
    AttributeMatchSelectionStrategy,
    Format,
    Modality,
    RoutingStrategy,
    SelectionStrategy,
)
from common_utils.models.entities import FilterAttribute


class ModelInfo(BaseModel):
    """Model information for responses."""

    model_name: str = Field(..., description="Model name")
    filter_attributes: List[FilterAttribute] = Field(
        default_factory=list, description="Filter attributes"
    )
    tags: Dict[str, Any] = Field(default_factory=dict, description="Model tags")
    api_contract: APIContract = Field(..., description="API contract")
    input_modality: List[Modality] = Field(..., description="Input modalities")
    output_modality: List[Modality] = Field(..., description="Output modalities")
    input_format: Format = Field(..., description="Input format")
    output_format: Format = Field(..., description="Output format")
    is_active: bool = Field(..., description="Whether the model is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModelListResponse(BaseModel):
    """Response model for a list of models."""

    success: bool = Field(..., description="Success status")
    data: List[ModelInfo] = Field(..., description="List of models")
    total_count: int = Field(..., description="Total number of models")
    page: Optional[int] = Field(None, description="Current page number")
    page_size: Optional[int] = Field(None, description="Page size")
    has_next: Optional[bool] = Field(..., description="Whether there are more pages")
    has_previous: Optional[bool] = Field(
        ..., description="Whether there are previous pages"
    )
    message: Optional[str] = Field(None, description="Response message")


class DeploymentInfo(BaseModel):
    """Deployment information for responses."""

    deployment_name: str = Field(..., description="Deployment name")
    filter_attributes: List[FilterAttribute] = Field(
        default_factory=list, description="Filter attributes"
    )
    tags: Dict[str, Any] = Field(default_factory=dict, description="Deployment tags")
    model_name: str = Field(..., description="Model name")
    tpm: int = Field(..., description="Tokens per minute")
    client_identifier: str = Field(..., description="Client identifier")
    path_identifier: str = Field(..., description="Path identifier")
    is_active: bool = Field(..., description="Whether the deployment is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class DeploymentListResponse(BaseModel):
    """Response model for a list of deployments."""

    success: bool = Field(..., description="Success status")
    data: List[DeploymentInfo] = Field(..., description="List of deployments")
    total_count: int = Field(..., description="Total number of deployments")
    page: Optional[int] = Field(None, description="Current page number")
    page_size: Optional[int] = Field(None, description="Page size")
    has_next: Optional[bool] = Field(..., description="Whether there are more pages")
    has_previous: Optional[bool] = Field(
        ..., description="Whether there are previous pages"
    )
    message: Optional[str] = Field(None, description="Response message")


class DeploymentConfig(BaseModel):
    """Deployment configuration for route planning levels in responses."""

    name: str = Field(..., description="Deployment name")
    weight: float = Field(default=1.0, description="Deployment weight")
    priority: int = Field(default=0, description="Deployment priority")


class RouteLevelModelConfig(BaseModel):
    """Model configuration for route planning levels in responses."""

    name: str = Field(..., description="Model name")
    weight: float = Field(default=1.0, description="Model weight")
    priority: int = Field(default=0, description="Model priority")
    deployments: List[DeploymentConfig] = Field(
        default_factory=list, description="Deployment configurations"
    )


class RoutePlanLevel(BaseModel):
    """Model for route planning level in responses."""

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
    attributes: Optional[List[FilterAttribute]] = Field(
        default=None, description="Attributes for attribute matching"
    )
    models: Optional[List[RouteLevelModelConfig]] = Field(
        default=None, description="Model configurations for explicit matching"
    )


class RoutePlanRetryConfig(BaseModel):
    """Model for route plan retry configuration in responses."""

    max_attempts: int = Field(..., description="Maximum retry attempts")
    max_time_seconds: int = Field(..., description="Maximum retry time in seconds")
    strict_max_time: bool = Field(
        ..., description="Whether to strictly enforce max time"
    )


class RoutePlanTimeoutConfig(BaseModel):
    """Model for route plan timeout configuration in responses."""

    timeout_seconds: int = Field(..., description="Timeout in seconds")


class RoutePlanConfiguration(BaseModel):
    """Route plan configuration for responses."""

    levels: List[RoutePlanLevel] = Field(..., description="Route planning levels")
    retry_config: RoutePlanRetryConfig = Field(..., description="Retry configuration")
    timeout_config: RoutePlanTimeoutConfig = Field(
        ..., description="Timeout configuration"
    )


class RoutePlanInfo(BaseModel):
    """Route plan information for responses."""

    id: str = Field(..., description="Route plan ID")
    route_plan_name: str = Field(..., description="Route plan name")
    route_plan: RoutePlanConfiguration = Field(
        ..., description="Route plan configuration"
    )
    is_active: bool = Field(..., description="Is active")
    created_at: str = Field(..., description="Created at")
    updated_at: str = Field(..., description="Updated at")


class RoutePlanListResponse(BaseModel):
    """Response model for a list of route plans."""

    success: bool = Field(..., description="Success status")
    data: List[RoutePlanInfo] = Field(..., description="List of route plans")
    total_count: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    message: Optional[str] = Field(None, description="Response message")


