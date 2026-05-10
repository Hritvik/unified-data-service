"""
Model bridge registry native models module.

This module provides native models with business logic for the model bridge registry.
These models serve as the core business logic layer between documents and API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field

from common_utils.enums import (
    AttributeMatchSelectionStrategy,
    RoutingStrategy,
    SelectionStrategy,
)
from common_utils.models.entities import FilterAttribute
from common_utils.timezone_utils import get_utc_now


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


class DeploymentConfigNative(BaseModel):
    """Native deployment configuration with business logic."""

    deployment_name: str = Field(..., description="Deployment name")
    filter_attributes: List[FilterAttribute] = Field(
        default_factory=list, description="Filter attributes"
    )
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags")
    model_name: str = Field(..., description="Model name")
    tpm: int = Field(..., description="Tokens per minute")
    client_identifier: str = Field(..., description="Client identifier")
    path_identifier: str = Field(..., description="Path identifier")
    is_active: bool = Field(default=True, description="Is active")
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @computed_field
    @property
    def is_high_capacity(self) -> bool:
        """Check if this is a high-capacity deployment."""
        return self.tpm >= 1000

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if this is a production deployment."""
        return self.tags.get("environment") == "production"

    @computed_field
    @property
    def tier_level(self) -> str:
        """Get the tier level of the deployment."""
        return self.tags.get("tier", "standard")

    def get_tag_value(self, tag_name: str) -> Optional[Any]:
        """Get the value of a specific tag."""
        return self.tags.get(tag_name)

    def has_filter_attribute(self, attribute_name: str) -> bool:
        """Check if the deployment has a specific filter attribute."""
        return any(attr.key == attribute_name for attr in self.filter_attributes)

    def get_filter_attribute(self, attribute_name: str) -> Optional[FilterAttribute]:
        """Get a specific filter attribute by name."""
        for attr in self.filter_attributes:
            if attr.key == attribute_name:
                return attr
        return None

    def can_handle_tpm(self, required_tpm: int) -> bool:
        """Check if the deployment can handle a required TPM load."""
        return self.tpm >= required_tpm

    def is_available_for_client(self, client_id: str) -> bool:
        """Check if the deployment is available for a specific client."""
        return self.client_identifier == client_id or self.client_identifier == "*"

    def get_endpoint_path(self, base_path: str = "") -> str:
        """Get the full endpoint path for this deployment."""
        if base_path:
            return f"{base_path}/{self.path_identifier}"
        return self.path_identifier

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "deployment_name": self.deployment_name,
            "filter_attributes": [attr.model_dump() for attr in self.filter_attributes],
            "tags": self.tags,
            "model_name": self.model_name,
            "tpm": self.tpm,
            "client_identifier": self.client_identifier,
            "path_identifier": self.path_identifier,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RoutePlanLevelRegistryNative(BaseModel):
    """Native route plan level with business logic for registry."""

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


class RoutePlanRetryConfigRegistryNative(BaseModel):
    """Native route plan retry configuration with business logic for registry."""

    max_attempts: int = Field(..., description="Maximum retry attempts")
    max_time_seconds: int = Field(..., description="Maximum retry time in seconds")
    strict_max_time: bool = Field(
        default=False, description="Whether to strictly enforce max time"
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


class RoutePlanTimeoutConfigRegistryNative(BaseModel):
    """Native route plan timeout configuration with business logic for registry."""

    timeout_seconds: int = Field(..., description="Timeout in seconds")

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


class RoutePlanConfigurationRegistryNative(BaseModel):
    """Native route plan configuration with business logic for registry."""

    levels: List[RoutePlanLevelRegistryNative] = Field(
        ..., description="Route planning levels"
    )
    retry_config: RoutePlanRetryConfigRegistryNative = Field(
        ..., description="Retry configuration"
    )
    timeout_config: RoutePlanTimeoutConfigRegistryNative = Field(
        ..., description="Timeout configuration"
    )

    @computed_field
    @property
    def total_levels(self) -> int:
        """Get the total number of routing levels."""
        return len(self.levels)

    @computed_field
    @property
    def has_multiple_levels(self) -> bool:
        """Check if the route plan has multiple levels."""
        return self.total_levels > 1

    @computed_field
    @property
    def primary_level(self) -> Optional[RoutePlanLevelRegistryNative]:
        """Get the primary routing level."""
        for level in self.levels:
            if level.is_primary_level:
                return level
        return None

    def get_level(self, level_number: int) -> Optional[RoutePlanLevelRegistryNative]:
        """Get a specific level by number."""
        for level in self.levels:
            if level.level == level_number:
                return level
        return None

    def is_valid_configuration(self) -> bool:
        """Check if the route plan configuration is valid."""
        if not self.levels:
            return False

        # Check for duplicate level numbers
        level_numbers = [level.level for level in self.levels]
        if len(level_numbers) != len(set(level_numbers)):
            return False

        # Check if levels are sequential
        sorted_levels = sorted(level_numbers)
        return sorted_levels == list(range(1, len(sorted_levels) + 1))


class RoutePlanInfoRegistryNative(BaseModel):
    """Native route plan information with business logic for registry."""

    id: str = Field(..., description="Route plan ID")
    route_plan_name: str = Field(..., description="Route plan name")
    route_plan: RoutePlanConfigurationRegistryNative = Field(
        ..., description="Route plan configuration"
    )
    is_active: bool = Field(default=True, description="Is active")
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @computed_field
    @property
    def is_complex_route(self) -> bool:
        """Check if this is a complex route with multiple levels."""
        return self.route_plan.has_multiple_levels

    @computed_field
    @property
    def has_retry_capability(self) -> bool:
        """Check if this route plan has retry capability."""
        return self.route_plan.retry_config.max_attempts > 1

    @computed_field
    @property
    def has_timeout_protection(self) -> bool:
        """Check if this route plan has timeout protection."""
        return self.route_plan.timeout_config.timeout_seconds > 0

    def get_level_configuration(
        self, level_number: int
    ) -> Optional[RoutePlanLevelRegistryNative]:
        """Get configuration for a specific level."""
        return self.route_plan.get_level(level_number)

    def can_handle_retry(self, current_attempt: int, elapsed_time: int) -> bool:
        """Check if the route plan can handle a retry request."""
        return self.route_plan.retry_config.can_retry(current_attempt, elapsed_time)

    def is_timeout_expired(self, elapsed_time: int) -> bool:
        """Check if the route plan timeout has expired."""
        return self.route_plan.timeout_config.is_expired(elapsed_time)

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "route_plan_name": self.route_plan_name,
            "route_plan": self.route_plan.model_dump(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
