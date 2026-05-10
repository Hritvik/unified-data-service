"""
Event handler interface and base implementations.

This module provides the base event handler interface and common
implementations for handling events in the distributed system.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from common_utils.logger import get_logger

from .event_models import BaseEvent, EventType

logger = get_logger(__name__)


class EventHandler(ABC):
    """
    Abstract base class for event handlers.

    Event handlers are responsible for processing specific types of events
    when they are received from the event broadcast system.
    """

    @abstractmethod
    async def can_handle(self, event: BaseEvent) -> bool:
        """
        Check if this handler can process the given event.

        Args:
            event: Event to check

        Returns:
            True if this handler can process the event
        """
        pass

    @abstractmethod
    async def handle(self, event: BaseEvent) -> Any:
        """
        Handle the given event.

        Args:
            event: Event to handle

        Returns:
            Result of event processing
        """
        pass

    @property
    @abstractmethod
    def handler_name(self) -> str:
        """Get the name of this handler."""
        pass

    @property
    @abstractmethod
    def supported_event_types(self) -> List[EventType]:
        """Get list of event types this handler supports."""
        pass


class EventHandlerRegistry:
    """
    Registry for managing event handlers.

    This registry allows registration and lookup of event handlers
    for different event types.
    """

    def __init__(self):
        """Initialize the event handler registry."""
        self._handlers: List[EventHandler] = []
        self.logger = logger

    def register_handler(self, handler: EventHandler) -> None:
        """
        Register an event handler.

        Args:
            handler: Event handler to register
        """
        self._handlers.append(handler)
        self.logger.info(f"Registered event handler: {handler.handler_name}")

    def unregister_handler(self, handler: EventHandler) -> None:
        """
        Unregister an event handler.

        Args:
            handler: Event handler to unregister
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            self.logger.info(f"Unregistered event handler: {handler.handler_name}")

    def get_handlers_for_event(self, event: BaseEvent) -> List[EventHandler]:
        """
        Get all handlers that can process the given event.

        Args:
            event: Event to find handlers for

        Returns:
            List of handlers that can process the event
        """
        handlers = []
        for handler in self._handlers:
            if event.event_type in handler.supported_event_types:
                handlers.append(handler)
        return handlers

    def get_handlers_by_type(self, event_type: EventType) -> List[EventHandler]:
        """
        Get all handlers for a specific event type.

        Args:
            event_type: Event type to find handlers for

        Returns:
            List of handlers for the event type
        """
        handlers = []
        for handler in self._handlers:
            if event_type in handler.supported_event_types:
                handlers.append(handler)
        return handlers

    def get_all_handlers(self) -> List[EventHandler]:
        """Get all registered handlers."""
        return self._handlers.copy()

    def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        self.logger.info("Cleared all event handlers")


class EventProcessor:
    """
    Event processor for handling events with registered handlers.

    This class processes events by finding appropriate handlers
    and executing them asynchronously.
    """

    def __init__(self, handler_registry: EventHandlerRegistry):
        """
        Initialize the event processor.

        Args:
            handler_registry: Registry containing event handlers
        """
        self._handler_registry = handler_registry
        self.logger = logger

    async def process_event(self, event: BaseEvent) -> Dict[str, Any]:
        """
        Process an event using registered handlers.

        Args:
            event: Event to process

        Returns:
            Dictionary with processing results
        """
        handlers = self._handler_registry.get_handlers_for_event(event)

        if not handlers:
            self.logger.warning(f"No handlers found for event type: {event.event_type}")
            return {
                "success": False,
                "message": f"No handlers found for event type: {event.event_type}",
                "handlers_executed": 0,
                "results": {},
            }

        results = {}
        successful_handlers = 0
        failed_handlers = 0

        # Execute all handlers concurrently
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._execute_handler(handler, event))
            tasks.append((handler, task))

        # Wait for all handlers to complete
        for handler, task in tasks:
            try:
                result = await task
                results[handler.handler_name] = {"success": True, "result": result}
                successful_handlers += 1
            except Exception as e:
                self.logger.error(f"Handler {handler.handler_name} failed: {e}")
                results[handler.handler_name] = {"success": False, "error": str(e)}
                failed_handlers += 1

        return {
            "success": successful_handlers > 0,
            "message": f"Processed event with {successful_handlers} successful handlers, {failed_handlers} failed",
            "handlers_executed": len(handlers),
            "successful_handlers": successful_handlers,
            "failed_handlers": failed_handlers,
            "results": results,
        }

    async def _execute_handler(self, handler: EventHandler, event: BaseEvent) -> Any:
        """
        Execute a single handler for an event.

        Args:
            handler: Handler to execute
            event: Event to process

        Returns:
            Result from handler
        """
        try:
            # Check if handler can handle this event
            if not await handler.can_handle(event):
                self.logger.warning(
                    f"Handler {handler.handler_name} cannot handle event {event.event_id}"
                )
                return None

            # Execute handler
            self.logger.info(
                f"Executing handler {handler.handler_name} for event {event.event_id}"
            )
            result = await handler.handle(event)

            self.logger.info(
                f"Handler {handler.handler_name} completed successfully for event {event.event_id}"
            )
            return result

        except Exception as e:
            self.logger.error(
                f"Handler {handler.handler_name} failed for event {event.event_id}: {e}"
            )
            raise
