"""
Event models for the generic event system.

This module defines the base event models and types that can be used
across the distributed system for event broadcasting and handling.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound="BaseEvent")


class EventType(str, Enum):
    """Enumeration of supported event types."""

    # Cache events
    CACHE_REFRESH_ALL = "cache_refresh_all"
    CACHE_REFRESH_SERVICE = "cache_refresh_service"
    CACHE_REFRESH_PATTERN = "cache_refresh_pattern"

    # System events
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_MAINTENANCE = "system_maintenance"

    # Custom events (can be extended)
    CUSTOM = "custom"


class BaseEvent(BaseModel, ABC):
    """
    Base class for all events in the system.

    This class provides common functionality for all events including
    event ID generation, timestamping, and serialization.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = Field(..., description="Type of the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_pod: Optional[str] = Field(None, description="Pod that generated the event")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event metadata"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    @abstractmethod
    def get_payload(self) -> Dict[str, Any]:
        """
        Get the event payload data.

        Returns:
            Dictionary containing the event-specific data
        """
        pass

    @classmethod
    @abstractmethod
    def from_payload(cls: Type[T], payload: Dict[str, Any], **kwargs) -> T:
        """
        Create an event instance from payload data.

        Args:
            payload: Event payload data
            **kwargs: Additional event attributes

        Returns:
            Event instance
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return self.dict()

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create event from dictionary."""
        return cls(**data)


class CacheRefreshAllEvent(BaseEvent):
    """Event for refreshing all caches."""

    event_type: EventType = EventType.CACHE_REFRESH_ALL

    def get_payload(self) -> Dict[str, Any]:
        """Get cache refresh all payload."""
        return {"refresh_all": True}

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], **kwargs) -> "CacheRefreshAllEvent":
        """Create from payload."""
        return cls(**kwargs)


class CacheRefreshServiceEvent(BaseEvent):
    """Event for refreshing a specific service cache."""

    event_type: EventType = EventType.CACHE_REFRESH_SERVICE
    service_name: str = Field(..., description="Name of the service to refresh")

    def get_payload(self) -> Dict[str, Any]:
        """Get cache refresh service payload."""
        return {"service_name": self.service_name}

    @classmethod
    def from_payload(
        cls, payload: Dict[str, Any], **kwargs
    ) -> "CacheRefreshServiceEvent":
        """Create from payload."""
        return cls(service_name=payload["service_name"], **kwargs)


class CacheRefreshPatternEvent(BaseEvent):
    """Event for refreshing caches by pattern."""

    event_type: EventType = EventType.CACHE_REFRESH_PATTERN
    pattern: str = Field(..., description="Pattern to match service names")

    def get_payload(self) -> Dict[str, Any]:
        """Get cache refresh pattern payload."""
        return {"pattern": self.pattern}

    @classmethod
    def from_payload(
        cls, payload: Dict[str, Any], **kwargs
    ) -> "CacheRefreshPatternEvent":
        """Create from payload."""
        return cls(pattern=payload["pattern"], **kwargs)


class SystemShutdownEvent(BaseEvent):
    """Event for system shutdown."""

    event_type: EventType = EventType.SYSTEM_SHUTDOWN
    reason: Optional[str] = Field(None, description="Reason for shutdown")
    graceful: bool = Field(True, description="Whether shutdown should be graceful")

    def get_payload(self) -> Dict[str, Any]:
        """Get system shutdown payload."""
        return {"reason": self.reason, "graceful": self.graceful}

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], **kwargs) -> "SystemShutdownEvent":
        """Create from payload."""
        return cls(
            reason=payload.get("reason"),
            graceful=payload.get("graceful", True),
            **kwargs,
        )


class CustomEvent(BaseEvent):
    """Event for custom application-specific events."""

    event_type: EventType = EventType.CUSTOM
    custom_type: str = Field(..., description="Custom event type identifier")
    data: Dict[str, Any] = Field(default_factory=dict, description="Custom event data")

    def get_payload(self) -> Dict[str, Any]:
        """Get custom event payload."""
        return {"custom_type": self.custom_type, "data": self.data}

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], **kwargs) -> "CustomEvent":
        """Create from payload."""
        return cls(
            custom_type=payload["custom_type"], data=payload.get("data", {}), **kwargs
        )


# Event type mapping for deserialization
EVENT_TYPE_MAPPING: Dict[EventType, Type[BaseEvent]] = {
    EventType.CACHE_REFRESH_ALL: CacheRefreshAllEvent,
    EventType.CACHE_REFRESH_SERVICE: CacheRefreshServiceEvent,
    EventType.CACHE_REFRESH_PATTERN: CacheRefreshPatternEvent,
    EventType.SYSTEM_SHUTDOWN: SystemShutdownEvent,
    EventType.CUSTOM: CustomEvent,
}


def create_event_from_dict(data: Dict[str, Any]) -> BaseEvent:
    """
    Create an event instance from dictionary data.

    Args:
        data: Dictionary containing event data

    Returns:
        Event instance

    Raises:
        ValueError: If event type is not supported
    """
    event_type = EventType(data.get("event_type"))

    if event_type not in EVENT_TYPE_MAPPING:
        raise ValueError(f"Unsupported event type: {event_type}")

    event_class = EVENT_TYPE_MAPPING[event_type]
    return event_class.from_dict(data)
