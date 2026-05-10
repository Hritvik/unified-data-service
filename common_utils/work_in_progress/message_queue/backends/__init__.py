try:
    from .kafka_backend import KafkaMessageQueue

    __all__ = [
        "KafkaMessageQueue",
    ]
except ImportError:
    # Kafka backend not available (kafka-python not installed)
    __all__ = []
