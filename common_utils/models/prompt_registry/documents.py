"""Beanie documents for prompt_registry.

3-level tree (siblings under namespace) plus an M:N reference:

    namespace (root, pk = `namespace`)
      ├── prompt_template (pk_field = id; natural identity is
      │                    (parent_id, name); references prompt_components
      │                    via a List[str] of "{type}.{name}" strings,
      │                    scoped to the same namespace)
      └── prompt_component (pk_field = id; natural identity is
                           (parent_id, component_type, component_name))

FKs use `parent_id` on child docs (uniform FK). Templates' `components`
field is resolved at read time by the hierarchical layer (`scope_field`
pins lookups to the same namespace).

Compound unique indexes on `(parent_id, name)` for templates and
`(parent_id, component_type, component_name)` for components.
"""

from datetime import datetime, timezone
from typing import Any, List

import pymongo
from beanie import Document
from pydantic import Field, field_validator

from common_utils.timezone_utils import get_utc_now

__all__ = [
    "NamespaceDocument",
    "PromptComponentDocument",
    "PromptTemplateDocument",
]


def _validate_datetime_field(v: Any) -> datetime:
    """Coerce `created_at`/`updated_at` to a UTC-aware ``datetime``.

    None → now-UTC. Valid ISO strings get parsed; aware datetimes are
    converted to UTC; naive datetimes are stamped as UTC. Bad strings raise
    rather than silently defaulting to now."""
    if v is None:
        return get_utc_now()
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp string {v!r}: {e}") from e
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    return v


class NamespaceDocument(Document):
    """Namespace. Natural-key (`namespace`, str) is the hierarchy id."""

    namespace: str = Field(..., description="Namespace identifier (natural key)")
    description: str = Field(...)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "namespaces"
        indexes = [
            pymongo.IndexModel(
                [("namespace", pymongo.ASCENDING)],
                name="namespaces_namespace_unique",
                unique=True,
            ),
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetime(cls, v: Any) -> datetime:
        return _validate_datetime_field(v)

    def update_timestamp(self) -> None:
        self.updated_at = get_utc_now()


class PromptComponentDocument(Document):
    """Prompt component. FK to namespace renamed `namespace` →
    `parent_id`. Natural identity is the compound (parent_id,
    component_type, component_name)."""

    parent_id: str = Field(
        ...,
        description="Parent namespace's `namespace` field (uniform FK).",
    )
    component_type: str = Field(...)
    component_name: str = Field(...)
    content: str = Field(...)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "prompt_components"
        indexes = [
            pymongo.IndexModel(
                [
                    ("parent_id", pymongo.ASCENDING),
                    ("component_type", pymongo.ASCENDING),
                    ("component_name", pymongo.ASCENDING),
                ],
                name="prompt_components_parent_type_name_unique",
                unique=True,
            ),
        ]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetime(cls, v: Any) -> datetime:
        return _validate_datetime_field(v)

    def update_timestamp(self) -> None:
        self.updated_at = get_utc_now()


class PromptTemplateDocument(Document):
    """Prompt template. FK to namespace renamed `namespace` →
    `parent_id`. Natural identity is the compound (parent_id, name).

    `components` retains the legacy List[str] of "{type}.{name}" refs;
    the hierarchical layer resolves them at read time, namespace-scoped
    by `parent_id`.
    """

    parent_id: str = Field(
        ...,
        description="Parent namespace's `namespace` field (uniform FK).",
    )
    name: str = Field(..., description="Template name (unique within parent)")
    template: str = Field(...)
    prompt_input: str = Field(...)
    components: List[str] = Field(
        default_factory=list,
        description="M:N references to components: '{type}.{name}' strings.",
    )
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "prompt_templates"
        indexes = [
            pymongo.IndexModel(
                [
                    ("parent_id", pymongo.ASCENDING),
                    ("name", pymongo.ASCENDING),
                ],
                name="prompt_templates_parent_name_unique",
                unique=True,
            ),
        ]

    @field_validator("components")
    @classmethod
    def _validate_components(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("components must be a list of 'type.name' strings")
        for item in v:
            if not isinstance(item, str):
                raise ValueError(
                    f"components must be a list of 'type.name' strings; got {item!r}"
                )
            parts = item.split(".")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(
                    f"component reference must be 'type.name' with non-empty parts; got {item!r}"
                )
        return v

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetime(cls, v: Any) -> datetime:
        return _validate_datetime_field(v)

    def update_timestamp(self) -> None:
        self.updated_at = get_utc_now()
