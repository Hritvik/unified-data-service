from enum import Enum

from .interfaces import IMessageQueue

try:
    from .backends.kafka_backend import KafkaMessageQueue

    KAFKA_AVAILABLE = True
except ImportError:
    # Kafka backend not available (kafka-python not installed)
    KafkaMessageQueue = None
    KAFKA_AVAILABLE = False


class MessageQueueBackend(Enum):
    KAFKA = "kafka"


class MessageQueueFactory:
    """Factory for creating message queue instances."""

    @staticmethod
    def create_message_queue(
        backend: MessageQueueBackend, kafka_producer=None, kafka_consumer=None
    ) -> IMessageQueue:
        """Create a message queue instance based on the backend."""

        if backend == MessageQueueBackend.KAFKA:
            if not KAFKA_AVAILABLE:
                raise ImportError(
                    "Kafka backend not available. Install kafka-python to use Kafka message queue."
                )
            if kafka_producer is None or kafka_consumer is None:
                raise ValueError(
                    "Kafka producer and consumer are required for Kafka backend"
                )
            return KafkaMessageQueue(kafka_producer, kafka_consumer)

        else:
            raise ValueError(f"Unsupported backend: {backend}")
