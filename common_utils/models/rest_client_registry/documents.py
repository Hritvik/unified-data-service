"""Beanie documents for rest_client_registry.

Endpoint's foreign key to its parent service is `parent_id` (uniform
parent-FK convention). The value stored is the parent service's
natural-key `name`.

Service is keyed by `name` for hierarchical operations (Beanie `_id` is
still present but is not part of the hierarchy graph).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pymongo
from beanie import Document
from pydantic import Field

from common_utils.enums import HTTPMethod
from common_utils.timezone_utils import get_utc_now

from .embedded_documents import (
    AuthConfigDocument,
    CircuitBreakerConfigDocument,
    ConnectionPoolConfigDocument,
    CredentialsConfigDocument,
    RetryConfigDocument,
    TimeoutConfigDocument,
)

__all__ = ["ServiceDocument", "EndpointDocument"]


class ServiceDocument(Document):
    """Service document. Natural-key (`name`) is the hierarchy id."""

    name: str = Field(..., description="Service name (natural key)")
    activate_at_startup: bool = Field(default=False)
    connection_pool: ConnectionPoolConfigDocument = Field(
        default_factory=ConnectionPoolConfigDocument
    )
    credentials: Optional[CredentialsConfigDocument] = Field(default=None)
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: TimeoutConfigDocument = Field(default_factory=TimeoutConfigDocument)
    circuit_breaker: CircuitBreakerConfigDocument = Field(
        default_factory=CircuitBreakerConfigDocument
    )
    retry: RetryConfigDocument = Field(default_factory=RetryConfigDocument)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "services"
        use_state_management = True
        indexes = [
            pymongo.IndexModel(
                [("name", pymongo.ASCENDING)],
                name="services_name_unique",
                unique=True,
            ),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True, exclude={"id"})


class EndpointDocument(Document):
    """Endpoint document. FK to parent service is `parent_id` holding
    the parent service's `name` (natural-key string)."""

    parent_id: str = Field(
        ...,
        description="Parent service's name (uniform FK convention).",
    )
    name: str = Field(..., description="Endpoint name (unique per parent)")
    path: str = Field(...)
    method: HTTPMethod = Field(default=HTTPMethod.GET)
    timeout: Optional[TimeoutConfigDocument] = Field(default=None)
    headers: Dict[str, str] = Field(default_factory=dict)
    path_params: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, str] = Field(default_factory=dict)
    auth: List[AuthConfigDocument] = Field(default_factory=list)
    circuit_breaker: Optional[CircuitBreakerConfigDocument] = Field(default=None)
    retry: Optional[RetryConfigDocument] = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    class Settings:
        name = "endpoints"
        use_state_management = True
        indexes = [
            pymongo.IndexModel(
                [
                    ("parent_id", pymongo.ASCENDING),
                    ("name", pymongo.ASCENDING),
                ],
                name="endpoints_parent_name_unique",
                unique=True,
            ),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True, exclude={"id"})
