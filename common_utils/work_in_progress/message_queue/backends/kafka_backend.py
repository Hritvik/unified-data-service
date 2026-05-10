import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from kafka import KafkaConsumer, KafkaProducer

from common_utils.logger import get_logger

from ..interfaces import IMessageQueue, IMessageQueueConsumer, IMessageQueueProducer
from ..models import ConsumerConfig, Message, MessageMetadata, QueueConfig

logger = get_logger(__name__)


class KafkaMessageQueueProducer(IMessageQueueProducer):
    """Kafka-based message queue producer."""

    def __init__(self, kafka_producer: KafkaProducer):
        self._producer = kafka_producer
        self.logger = logger

    async def send_message(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[MessageMetadata] = None,
    ) -> str:
        """Send a message to a Kafka topic."""
        try:
            # Generate message ID
            message_id = str(uuid.uuid4())

            # Create message metadata
            if metadata is None:
                metadata = MessageMetadata(message_id=message_id)
            else:
                metadata.message_id = message_id

            # Create message
            message = Message(topic=topic, key=key, value=value, metadata=metadata)

            # Add headers if provided
            if headers:
                message.metadata.headers.update(headers)

            # Serialize message
            message_data = {
                "message_id": message_id,
                "key": key or "",
                "value": value,
                "metadata": message.metadata.dict(),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Send to Kafka
            future = self._producer.send(
                topic=topic,
                key=key.encode("utf-8") if key else None,
                value=json.dumps(message_data).encode("utf-8"),
                headers=[(k, v.encode("utf-8")) for k, v in (headers or {}).items()],
            )

            # Wait for confirmation
            future.get(timeout=10)

            self.logger.debug(f"Sent message {message_id} to topic {topic}")
            return message_id

        except Exception as e:
            self.logger.error(f"Error sending message to topic {topic}: {e}")
            raise

    async def send_batch(self, topic: str, messages: List[Message]) -> List[str]:
        """Send multiple messages in a batch."""
        message_ids = []

        for message in messages:
            message_id = await self.send_message(
                topic=message.topic,
                value=message.value,
                key=message.key,
                headers=message.metadata.headers,
                metadata=message.metadata,
            )
            message_ids.append(message_id)

        return message_ids

    async def create_topic(self, config: QueueConfig) -> bool:
        """Create a new topic."""
        try:
            # Kafka topic creation is typically handled by admin client
            # This is a placeholder for the interface
            self.logger.info(f"Topic creation requested for {config.name}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating topic {config.name}: {e}")
            return False

    async def delete_topic(self, topic: str) -> bool:
        """Delete a topic."""
        try:
            # Kafka topic deletion is typically handled by admin client
            # This is a placeholder for the interface
            self.logger.info(f"Topic deletion requested for {topic}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting topic {topic}: {e}")
            return False

    async def get_topic_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get information about a topic."""
        try:
            # Kafka topic info retrieval is typically handled by admin client
            # This is a placeholder for the interface
            return {"topic": topic, "partitions": 1}
        except Exception as e:
            self.logger.error(f"Error getting topic info for {topic}: {e}")
            return None


class KafkaMessageQueueConsumer(IMessageQueueConsumer):
    """Kafka-based message queue consumer."""

    def __init__(self, kafka_consumer: KafkaConsumer):
        self._consumer = kafka_consumer
        self.logger = logger

    async def subscribe(self, topics: List[str], config: ConsumerConfig) -> None:
        """Subscribe to topics."""
        try:
            self._consumer.subscribe(topics)
            self.logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            self.logger.error(f"Error subscribing to topics {topics}: {e}")
            raise

    async def poll(self, timeout_ms: int = 1000) -> List[Message]:
        """Poll for messages."""
        try:
            message_pack = self._consumer.poll(timeout_ms=timeout_ms)
            messages = []

            for topic_partition, records in message_pack.items():
                for record in records:
                    try:
                        # Parse message data
                        message_data = json.loads(record.value.decode("utf-8"))

                        # Create message object
                        message = Message(
                            topic=record.topic,
                            key=record.key.decode("utf-8") if record.key else None,
                            value=message_data["value"],
                            metadata=MessageMetadata(**message_data["metadata"]),
                        )

                        messages.append(message)

                    except Exception as e:
                        self.logger.error(
                            f"Error parsing message from {record.topic}: {e}"
                        )
                        continue

            return messages

        except Exception as e:
            self.logger.error(f"Error polling messages: {e}")
            return []

    async def commit(self, message: Message) -> None:
        """Commit message offset."""
        try:
            # Kafka handles offset commit automatically with enable_auto_commit=True
            # This is a placeholder for manual commit if needed
            self.logger.debug(
                f"Commit requested for message {message.metadata.message_id}"
            )
        except Exception as e:
            self.logger.error(
                f"Error committing message {message.metadata.message_id}: {e}"
            )

    async def commit_batch(self, messages: List[Message]) -> None:
        """Commit multiple message offsets."""
        for message in messages:
            await self.commit(message)

    async def close(self) -> None:
        """Close the consumer."""
        self._consumer.close()


class KafkaMessageQueue(IMessageQueue):
    """Kafka-based message queue implementation."""

    def __init__(self, kafka_producer: KafkaProducer, kafka_consumer: KafkaConsumer):
        self._producer = kafka_producer
        self._consumer = kafka_consumer
        self.logger = logger

    async def get_producer(self) -> IMessageQueueProducer:
        """Get a producer instance."""
        return KafkaMessageQueueProducer(self._producer)

    async def get_consumer(self, config: ConsumerConfig) -> IMessageQueueConsumer:
        """Get a consumer instance."""
        return KafkaMessageQueueConsumer(self._consumer)

    async def get_queue_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get queue information."""
        try:
            # Kafka topic info retrieval is typically handled by admin client
            # This is a placeholder for the interface
            return {"topic": topic, "partitions": 1}
        except Exception as e:
            self.logger.error(f"Error getting queue info for {topic}: {e}")
            return None

    async def close(self) -> None:
        """Close the message queue connection."""
        self._producer.close()
        self._consumer.close()
