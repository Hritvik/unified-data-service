"""Beanie documents for model_bridge_registry.

2-level tree:

    model (root, pk = model_name)
      └── deployment (pk = deployment_name, parent_id = model.model_name)

Deployment's foreign key is renamed `model_name` → `parent_id` (uniform
FK convention). Value stored is still the parent model's natural-key
`model_name` string, so import/export and recreate cycles preserve the
relationship.

`model_name` and `deployment_name` have explicit unique indexes.

RoutePlan is standalone — it sideways-references models and deployments
by name and is not part of the model→deployment ownership tree.
"""

from datetime import datetime
from typing import Any, Dict, List

import pymongo
from beanie import Document
from pydantic import ConfigDict, Field, field_validator

from common_utils.enums import APIContract, Format, Modality
from common_utils.models.entities import FilterAttribute
from common_utils.models.model_bridge_registry.route_plan_subdocs import (
    RoutePlanConfigurationDocument,
)
from common_utils.timezone_utils import get_utc_now, parse_datetime_from_standard_format

__all__ = ["ModelDocument", "DeploymentDocument", "RoutePlanDocument"]


def _default_dict() -> Dict[str, Any]:
    return {}


def _validate_datetime_field(v: Any) -> datetime:
    """Shared `created_at`/`updated_at` coercion for these documents.

    ``None`` defaults to ``get_utc_now()``; valid ISO-ish strings are parsed
    via the project's standard parser; anything else raises with the offending
    value embedded so bad imports surface instead of silently being rewritten
    to "now"."""
    if v is None:
        return get_utc_now()
    if isinstance(v, str):
        try:
            return parse_datetime_from_standard_format(v)
        except ValueError as e:
            raise ValueError(f"Invalid timestamp string {v!r}: {e}") from e
    return v


class ModelDocument(Document):
    """Model. Natural-key (`model_name`) is the hierarchy id."""

    model_config = ConfigDict(
        validate_assignment=True, arbitrary_types_allowed=True, populate_by_name=True
    )

    model_name: str = Field(..., description="Model name (natural key)")
    filter_attributes: List[FilterAttribute] = Field(default_factory=list)
    tags: Dict[str, Any] = Field(default_factory=_default_dict)
    api_contract: APIContract = Field(...)
    input_modality: List[Modality] = Field(...)
    output_modality: List[Modality] = Field(...)
    input_format: Format = Field(...)
    output_format: Format = Field(...)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "models"
        indexes = [
            pymongo.IndexModel(
                [("model_name", pymongo.ASCENDING)],
                name="models_model_name_unique",
                unique=True,
            ),
            [("input_modality", 1)],
            [("output_modality", 1)],
            [("is_active", 1)],
            [("api_contract", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetime(cls, v: Any) -> datetime:
        return _validate_datetime_field(v)

    @field_validator("input_modality", "output_modality", mode="before")
    @classmethod
    def _validate_modality(cls, v: Any) -> List[Modality]:
        if isinstance(v, str):
            return [Modality(v)]
        if isinstance(v, list):
            return [Modality(item) if isinstance(item, str) else item for item in v]
        return v

    @field_validator("api_contract", mode="before")
    @classmethod
    def _validate_api_contract(cls, v: Any) -> APIContract:
        if isinstance(v, str):
            return APIContract(v)
        return v

    @field_validator("input_format", "output_format", mode="before")
    @classmethod
    def _validate_format(cls, v: Any) -> Format:
        if isinstance(v, str):
            return Format(v)
        return v


class DeploymentDocument(Document):
    """Deployment. FK to parent model renamed `model_name` →
    `parent_id`. Natural-key (`deployment_name`) is the hierarchy id."""

    model_config = ConfigDict(
        validate_assignment=True, arbitrary_types_allowed=True, populate_by_name=True
    )

    deployment_name: str = Field(
        ..., description="Deployment name (natural key)"
    )
    parent_id: str = Field(
        ...,
        description="Parent model's `model_name` (uniform FK convention).",
    )
    filter_attributes: List[FilterAttribute] = Field(...)
    tags: Dict[str, Any] = Field(...)
    tpm: int = Field(..., description="Tokens per minute")
    client_identifier: str = Field(...)
    path_identifier: str = Field(...)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "deployments"
        indexes = [
            pymongo.IndexModel(
                [("deployment_name", pymongo.ASCENDING)],
                name="deployments_deployment_name_unique",
                unique=True,
            ),
            [("parent_id", 1)],
            [("client_identifier", 1)],
            [("path_identifier", 1)],
            [("is_active", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetime(cls, v: Any) -> datetime:
        return _validate_datetime_field(v)

    @field_validator("tpm", mode="before")
    @classmethod
    def _validate_tpm(cls, v: Any) -> int:
        v = int(v)
        if v < 0:
            raise ValueError("TPM must be non-negative")
        return v


class RoutePlanDocument(Document):
    """Route plan. Standalone entity — not part of the
    model→deployment ownership tree.

    A route plan sideways-references both models and deployments by
    natural name through its nested ``route_plan`` configuration. The
    layer keeps the nested shape verbatim (RoutePlanConfigurationDocument
    is reused) with a unique index on ``route_plan_name``.
    """

    model_config = ConfigDict(
        validate_assignment=True, arbitrary_types_allowed=True, populate_by_name=True
    )

    route_plan_name: str = Field(
        ..., description="Route plan name (natural key)"
    )
    route_plan: RoutePlanConfigurationDocument = Field(
        ..., description="Route plan configuration"
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "route_plans"
        indexes = [
            pymongo.IndexModel(
                [("route_plan_name", pymongo.ASCENDING)],
                name="route_plans_route_plan_name_unique",
                unique=True,
            ),
            [("is_active", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetime(cls, v: Any) -> datetime:
        return _validate_datetime_field(v)
