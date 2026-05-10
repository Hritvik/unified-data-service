try:
    from .backends.kafka_backend import KafkaMessageQueue
except ImportError:
    # Kafka backend not available (kafka-python not installed)
    KafkaMessageQueue = None
from .factory import MessageQueueBackend, MessageQueueFactory
from .interfaces import IMessageQueue, IMessageQueueConsumer, IMessageQueueProducer
from .lifecycle import MessageQueueLifecycleManager, message_queue_lifecycle
from .models import (
    ConsumerConfig,
    Message,
    MessageMetadata,
    MessagePriority,
    MessageStatus,
    QueueConfig,
)
from .monitoring import (
    MessageQueueHealthChecker,
    MessageQueueMetrics,
    message_queue_health_checker,
    message_queue_metrics,
    track_message_operation,
)

__all__ = [
    "IMessageQueue",
    "IMessageQueueProducer",
    "IMessageQueueConsumer",
    "Message",
    "MessageMetadata",
    "QueueConfig",
    "ConsumerConfig",
    "MessagePriority",
    "MessageStatus",
    "MessageQueueFactory",
    "MessageQueueBackend",
    "message_queue_lifecycle",
    "MessageQueueLifecycleManager",
    "message_queue_metrics",
    "message_queue_health_checker",
    "MessageQueueMetrics",
    "MessageQueueHealthChecker",
    "track_message_operation",
]

# Add KafkaMessageQueue to __all__ only if it's available
if KafkaMessageQueue is not None:
    __all__.append("KafkaMessageQueue")
