"""
Event registry for managing event handlers and types.

This module provides a centralized registry for managing event handlers
and their associations with event types.
"""

from typing import Any, Dict, List

from common_utils.logger import get_logger

from .event_handler import EventHandler, EventHandlerRegistry
from .event_models import BaseEvent, EventType

logger = get_logger(__name__)


class EventRegistry:
    """
    Central registry for managing event handlers and types.

    This registry provides a centralized way to manage event handlers
    and their associations with event types across the application.
    """

    def __init__(self):
        """Initialize the event registry."""
        self._handler_registry = EventHandlerRegistry()
        self._event_type_handlers: Dict[EventType, List[EventHandler]] = {}
        self.logger = logger

    def register_handler(self, handler: EventHandler) -> None:
        """
        Register an event handler.

        Args:
            handler: Event handler to register
        """
        self._handler_registry.register_handler(handler)

        # Update event type mapping
        for event_type in handler.supported_event_types:
            if event_type not in self._event_type_handlers:
                self._event_type_handlers[event_type] = []
            self._event_type_handlers[event_type].append(handler)

        self.logger.info(
            f"Registered handler {handler.handler_name} for event types: {handler.supported_event_types}"
        )

    def unregister_handler(self, handler: EventHandler) -> None:
        """
        Unregister an event handler.

        Args:
            handler: Event handler to unregister
        """
        self._handler_registry.unregister_handler(handler)

        # Update event type mapping
        for event_type in handler.supported_event_types:
            if event_type in self._event_type_handlers:
                if handler in self._event_type_handlers[event_type]:
                    self._event_type_handlers[event_type].remove(handler)

        self.logger.info(f"Unregistered handler {handler.handler_name}")

    def get_handlers_for_event_type(self, event_type: EventType) -> List[EventHandler]:
        """
        Get all handlers for a specific event type.

        Args:
            event_type: Event type to get handlers for

        Returns:
            List of handlers for the event type
        """
        return self._event_type_handlers.get(event_type, []).copy()

    def get_handlers_for_event(self, event: BaseEvent) -> List[EventHandler]:
        """
        Get all handlers that can process the given event.

        Args:
            event: Event to get handlers for

        Returns:
            List of handlers that can process the event
        """
        return self._handler_registry.get_handlers_for_event(event)

    def get_all_handlers(self) -> List[EventHandler]:
        """Get all registered handlers."""
        return self._handler_registry.get_all_handlers()

    def get_supported_event_types(self) -> List[EventType]:
        """Get all supported event types."""
        return list(self._event_type_handlers.keys())

    def get_handler_count(self) -> int:
        """Get total number of registered handlers."""
        return len(self._handler_registry.get_all_handlers())

    def get_handler_count_for_type(self, event_type: EventType) -> int:
        """Get number of handlers for a specific event type."""
        return len(self._event_type_handlers.get(event_type, []))

    def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        self._handler_registry.clear_handlers()
        self._event_type_handlers.clear()
        self.logger.info("Cleared all event handlers")

    def get_status(self) -> Dict[str, Any]:
        """
        Get registry status information.

        Returns:
            Dictionary with registry status
        """
        return {
            "total_handlers": self.get_handler_count(),
            "supported_event_types": [
                et.value for et in self.get_supported_event_types()
            ],
            "handlers_by_type": {
                et.value: self.get_handler_count_for_type(et)
                for et in self.get_supported_event_types()
            },
            "handlers": [
                {
                    "name": handler.handler_name,
                    "supported_types": [
                        et.value for et in handler.supported_event_types
                    ],
                }
                for handler in self.get_all_handlers()
            ],
        }
