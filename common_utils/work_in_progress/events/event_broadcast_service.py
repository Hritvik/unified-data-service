"""
Generic event broadcast service for distributed event handling.

This service provides a generic way to broadcast and receive events
across multiple pods in a distributed system using Redis Pub/Sub.
"""

import asyncio
import uuid
from typing import Any, Dict, Optional

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from .event_handler import EventHandlerRegistry, EventProcessor
from .event_models import BaseEvent, EventType, create_event_from_dict

logger = get_logger(__name__)


class EventBroadcastService:
    """
    Generic service for broadcasting and receiving events across pods.

    This service handles:
    - Publishing events to Redis
    - Listening for events from other pods
    - Processing events with registered handlers
    - Managing event lifecycle and deduplication
    """

    def __init__(
        self,
        redis_client: RedisClient,
        handler_registry: EventHandlerRegistry,
        pod_id: Optional[str] = None,
        channel_prefix: str = "events",
        max_processed_events: int = 1000,
    ):
        """
        Initialize the event broadcast service.

        Args:
            redis_client: Redis client for Pub/Sub operations
            handler_registry: Registry containing event handlers
            pod_id: Unique identifier for this pod (defaults to generated UUID)
            channel_prefix: Prefix for Redis channels
            max_processed_events: Maximum number of processed events to keep in memory
        """
        self._redis_client = redis_client
        self._handler_registry = handler_registry
        self._event_processor = EventProcessor(handler_registry)
        self._pod_id = pod_id or str(uuid.uuid4())
        self._channel_prefix = channel_prefix
        self._event_channel = f"{channel_prefix}:events"
        self._response_channel = f"{channel_prefix}:responses"
        self._max_processed_events = max_processed_events
        self._listener_task: Optional[asyncio.Task] = None
        self._is_listening = False
        self._processed_events: set = set()
        self.logger = logger

        logger.info(f"EventBroadcastService initialized for pod: {self._pod_id}")

    async def start_listening(self) -> None:
        """Start listening for events."""
        if self._is_listening:
            self.logger.warning("Already listening for events")
            return

        try:
            # Subscribe to event channel
            self._pubsub = await self._redis_client.subscribe(self._event_channel)
            if not self._pubsub:
                self.logger.error(f"Failed to subscribe to {self._event_channel}")
                self._is_listening = False
                return

            self._is_listening = True

            # Start background task to process events
            self._listener_task = asyncio.create_task(self._listen_for_events())

            self.logger.info(
                f"Started listening for events on channel: {self._event_channel}"
            )
        except Exception as e:
            self.logger.error(f"Failed to start listening for events: {e}")
            raise

    async def stop_listening(self) -> None:
        """Stop listening for events."""
        if not self._is_listening:
            return

        self._is_listening = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "_pubsub"):
            await self._pubsub.close()

        self.logger.info("Stopped listening for events")

    async def broadcast_event(self, event: BaseEvent) -> str:
        """
        Broadcast an event to all pods.

        Args:
            event: Event to broadcast

        Returns:
            Event ID for tracking
        """
        try:
            # Set source pod if not already set
            if not event.source_pod:
                event.source_pod = self._pod_id

            # Serialize event
            event_data = event.to_dict()

            # Publish to Redis
            subscribers = await self._redis_client.publish(
                self._event_channel, event_data
            )

            self.logger.info(
                f"Broadcasted event {event.event_id} to {subscribers} subscribers. "
                f"Type: {event.event_type}, Source: {event.source_pod}"
            )

            return event.event_id
        except Exception as e:
            self.logger.error(f"Failed to broadcast event: {e}")
            raise

    async def broadcast_event_by_type(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Broadcast an event by type and payload.

        Args:
            event_type: Type of event to broadcast
            payload: Event payload data
            metadata: Optional event metadata

        Returns:
            Event ID for tracking
        """
        # Create event instance based on type
        event_data = {
            "event_type": event_type,
            "source_pod": self._pod_id,
            "metadata": metadata or {},
        }

        # Add payload data
        event_data.update(payload)

        # Create event instance
        event = create_event_from_dict(event_data)

        return await self.broadcast_event(event)

    async def _listen_for_events(self) -> None:
        """Background task to listen for and process events."""
        try:
            async for message in self._pubsub.listen():
                if not self._is_listening:
                    break

                await self._process_message(message)
        except asyncio.CancelledError:
            self.logger.info("Event listener cancelled")
        except Exception as e:
            self.logger.error(f"Error in event listener: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """
        Process a received event message.

        Args:
            message: Redis Pub/Sub message
        """
        try:
            # Skip subscription confirmation messages
            if message.get("type") in ["subscribe", "psubscribe"]:
                return

            # Get event data
            event_data = message.get("data")
            if not event_data:
                return

            # Parse event
            event = create_event_from_dict(event_data)

            # Skip events from this pod (avoid infinite loops)
            if event.source_pod == self._pod_id:
                return

            # Skip already processed events
            if event.event_id in self._processed_events:
                return

            # Mark event as processed
            self._processed_events.add(event.event_id)

            # Clean up old processed events
            if len(self._processed_events) > self._max_processed_events:
                # Keep only the most recent half
                events_list = list(self._processed_events)
                self._processed_events = set(
                    events_list[-self._max_processed_events // 2 :]
                )

            self.logger.info(
                f"Processing event {event.event_id} from pod {event.source_pod}"
            )

            # Process event with registered handlers
            result = await self._event_processor.process_event(event)

            self.logger.info(f"Event {event.event_id} processed: {result}")

        except Exception as e:
            self.logger.error(f"Error processing event message: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """
        Get service status information.

        Returns:
            Dictionary with service status
        """
        return {
            "pod_id": self._pod_id,
            "is_listening": self._is_listening,
            "event_channel": self._event_channel,
            "response_channel": self._response_channel,
            "processed_events_count": len(self._processed_events),
            "listener_task_running": self._listener_task is not None
            and not self._listener_task.done(),
            "registered_handlers": len(self._handler_registry.get_all_handlers()),
        }

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.stop_listening()
        self.logger.info("EventBroadcastService closed")
