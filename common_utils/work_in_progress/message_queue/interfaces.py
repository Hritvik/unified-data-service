from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import ConsumerConfig, Message, MessageMetadata, QueueConfig


class IMessageQueueProducer(ABC):
    """Interface for message queue producers."""

    @abstractmethod
    async def send_message(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[MessageMetadata] = None,
    ) -> str:
        """Send a message to a topic."""
        pass

    @abstractmethod
    async def send_batch(self, topic: str, messages: List[Message]) -> List[str]:
        """Send multiple messages in a batch."""
        pass

    @abstractmethod
    async def create_topic(self, config: QueueConfig) -> bool:
        """Create a new topic/queue."""
        pass

    @abstractmethod
    async def delete_topic(self, topic: str) -> bool:
        """Delete a topic/queue."""
        pass

    @abstractmethod
    async def get_topic_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get information about a topic."""
        pass


class IMessageQueueConsumer(ABC):
    """Interface for message queue consumers."""

    @abstractmethod
    async def subscribe(self, topics: List[str], config: ConsumerConfig) -> None:
        """Subscribe to topics."""
        pass

    @abstractmethod
    async def poll(self, timeout_ms: int = 1000) -> List[Message]:
        """Poll for messages."""
        pass

    @abstractmethod
    async def commit(self, message: Message) -> None:
        """Commit message offset."""
        pass

    @abstractmethod
    async def commit_batch(self, messages: List[Message]) -> None:
        """Commit multiple message offsets."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the consumer."""
        pass


class IMessageQueue(ABC):
    """Main interface for message queue operations."""

    @abstractmethod
    async def get_producer(self) -> IMessageQueueProducer:
        """Get a producer instance."""
        pass

    @abstractmethod
    async def get_consumer(self, config: ConsumerConfig) -> IMessageQueueConsumer:
        """Get a consumer instance."""
        pass

    @abstractmethod
    async def get_queue_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get queue information."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the message queue connection."""
        pass
