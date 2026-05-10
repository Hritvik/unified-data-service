"""Nested sub-documents for route plan configuration.

Originally lived alongside older route-plan document layouts; the current
``RoutePlanDocument`` (see ``documents.py``) reuses the same nested schema
verbatim (same field shapes, same Mongo BSON layout), so these sub-models
are extracted here to outlive the legacy parent. Importing modules:

  - ``common_utils.models.model_bridge_registry.documents.RoutePlanDocument``
    (route_plan field type)
  - ``common_utils.models.model_bridge_registry.converters`` (legacy
    document-to-native converter, still used by read paths)
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from common_utils.enums import (
    AttributeMatchSelectionStrategy,
    RoutingStrategy,
    SelectionStrategy,
)
from common_utils.models.entities import FilterAttribute


class DeploymentConfigDocument(BaseModel):
    """Document model for route level deployment configuration."""

    name: str = Field(..., description="Deployment name")
    weight: Optional[float] = Field(default=1.0, description="Deployment weight")
    priority: Optional[int] = Field(default=1, description="Deployment priority")


class RouteLevelModelConfigDocument(BaseModel):
    """Document model for route level model configuration."""

    name: str = Field(..., description="Model name")
    weight: Optional[float] = Field(default=1.0, description="Model weight")
    priority: Optional[int] = Field(default=1, description="Model priority")
    deployments: Optional[List[DeploymentConfigDocument]] = Field(
        default=None, description="Deployment configurations"
    )


class RoutePlanLevelDocument(BaseModel):
    """Document model for route plan level."""

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
    routing_strategy: Optional[RoutingStrategy] = Field(
        default=None, description="Routing strategy for deployment selection"
    )
    attributes: Optional[List[FilterAttribute]] = Field(
        default=None, description="Attributes for attribute matching"
    )
    models: Optional[List[RouteLevelModelConfigDocument]] = Field(
        default=None, description="Model configurations for explicit matching"
    )


class RoutePlanRetryConfigDocument(BaseModel):
    """Document model for route plan retry configuration."""

    max_attempts: int = Field(..., ge=1, description="Maximum retry attempts")
    max_time_seconds: int = Field(
        ..., ge=1, description="Maximum retry time in seconds"
    )
    strict_max_time: bool = Field(
        default=False, description="Whether to strictly enforce max time"
    )


class RoutePlanTimeoutConfigDocument(BaseModel):
    """Document model for route plan timeout configuration."""

    timeout_seconds: int = Field(..., ge=1, description="Timeout in seconds")


class RoutePlanConfigurationDocument(BaseModel):
    """Document model for route plan configuration."""

    levels: List[RoutePlanLevelDocument] = Field(
        ..., min_length=1, description="Route planning levels"
    )
    retry_config: RoutePlanRetryConfigDocument = Field(
        ..., description="Retry configuration"
    )
    timeout_config: RoutePlanTimeoutConfigDocument = Field(
        ..., description="Timeout configuration"
    )
