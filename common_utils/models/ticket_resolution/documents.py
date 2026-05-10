"""
Ticket resolution documents module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from datetime import datetime
from typing import Any, Dict, Optional

import pymongo
from beanie import Document
from pydantic import Field, field_validator

from common_utils.timezone_utils import get_utc_now, parse_datetime_from_standard_format


class OldIssueCategoryDocument(Document):
    """Beanie model for old issue categories stored in MongoDB."""

    category_id: int = Field(..., description="Category ID from the original mapping")
    category_title: str = Field(..., description="Category title/name")
    is_others: bool = Field(
        default=False,
        description="Whether this is an 'Others' or 'Miscellaneous' category",
    )
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "old_issue_categories"
        indexes = [
            pymongo.IndexModel([("category_id", 1)], unique=True),
            [("category_title", 1)],
            [("is_others", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> datetime:
        """Validate and convert datetime fields."""
        if v is None:
            return get_utc_now()
        if isinstance(v, str):
            try:
                return parse_datetime_from_standard_format(v)
            except ValueError:
                return get_utc_now()
        return v

    async def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()
        await self.save()


class IssueCategoryDocument(Document):
    """Beanie model for issue categories stored in MongoDB."""

    category_id: int = Field(..., description="Category ID from the original mapping")
    category_title: str = Field(..., description="Category title/name")
    category_description: str = Field(..., description="Category description")
    is_others: bool = Field(
        default=False,
        description="Whether this is an 'Others' or 'Miscellaneous' category",
    )
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "issue_categories"
        indexes = [
            pymongo.IndexModel([("category_id", 1)], unique=True),
            [("category_title", 1)],
            [("category_description", 1)],
            [("is_others", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> datetime:
        """Validate and convert datetime fields."""
        if v is None:
            return get_utc_now()
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return get_utc_now()
        return v

    async def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()
        await self.save()


class OldICSubcategoryMappingDocument(Document):
    """Beanie model for old IC subcategory mapping stored in MongoDB."""

    category_id: int = Field(..., description="Category ID")
    sub_category_id: int = Field(..., description="Sub Category ID")
    sub_category_title: str = Field(..., description="Sub Category Title")
    is_others: bool = Field(
        default=False,
        description="Whether this is an 'Others' or 'Miscellaneous' category",
    )
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "old_ic_subcategory_mappings"
        indexes = [
            pymongo.IndexModel([("sub_category_id", 1)], unique=True),
            [("category_id", 1)],
            [("sub_category_title", 1)],
            [("is_others", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> datetime:
        """Validate and convert datetime fields."""
        if v is None:
            return get_utc_now()
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return get_utc_now()
        return v

    async def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()
        await self.save()


class ICSubcategoryMappingDocument(Document):
    """Beanie model for IC subcategory mapping stored in MongoDB."""

    category_id: int = Field(..., description="Category ID")
    sub_category_id: int = Field(..., description="Sub Category ID")
    sub_category_title: str = Field(..., description="Sub Category Title")
    sub_category_description: str = Field(..., description="Sub Category Description")
    is_others: bool = Field(
        default=False,
        description="Whether this is an 'Others' or 'Miscellaneous' category",
    )
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "ic_subcategory_mappings"
        indexes = [
            pymongo.IndexModel([("sub_category_id", 1)], unique=True),
            [("category_id", 1)],
            [("sub_category_title", 1)],
            [("sub_category_description", 1)],
            [("is_others", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> datetime:
        """Validate and convert datetime fields."""
        if v is None:
            return get_utc_now()
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return get_utc_now()
        return v

    async def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()
        await self.save()


class DispositionSCMapDocument(Document):
    """Beanie model for disposition_sc_map collection."""

    l2_ss: str = Field(..., description="L2 SS value")
    sub_category_id: int = Field(..., description="Sub Category ID")
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "disposition_sc_map"
        indexes = [
            pymongo.IndexModel([("l2_ss", 1)], unique=True),
            [("sub_category_id", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> datetime:
        """Validate and convert datetime fields."""
        if v is None:
            return get_utc_now()
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return get_utc_now()
        return v

    async def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()
        await self.save()


class ResponseTemplateDocument(Document):
    """Beanie model for scenario response templates stored in MongoDB."""

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
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "response_templates"
        indexes = [
            pymongo.IndexModel(
                [("sub_category_id", 1), ("scenario_identifier", 1)],
                unique=True,
            ),
            [("scenario_identifier", 1)],
            [("created_at", -1)],
            [("updated_at", -1)],
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> datetime:
        """Validate and convert datetime fields."""
        if v is None:
            return get_utc_now()
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return get_utc_now()
        return v

    async def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = get_utc_now()
        await self.save()
