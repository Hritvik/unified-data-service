import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from common_utils.logger import get_logger

from .interfaces import IMessageQueue
from .models import ConsumerConfig, Message, MessageMetadata

logger = get_logger(__name__)


class DeadLetterQueueService:
    """Service for managing dead letter queues."""

    def __init__(
        self,
        message_queue: IMessageQueue,
        dlq_topic: str = "dlq-events",
        retry_topic: str = "retry-events",
        max_retries: int = 3,
        base_retry_delay: int = 60,
        max_retry_delay: int = 3600,
    ):
        self._mq = message_queue
        self._dlq_topic = dlq_topic
        self._retry_topic = retry_topic
        self._max_retries = max_retries
        self._base_retry_delay = base_retry_delay
        self._max_retry_delay = max_retry_delay
        self._is_processing = False
        self._processing_task: Optional[asyncio.Task] = None
        self.logger = logger

    async def send_to_dlq(
        self,
        original_topic: str,
        message: Message,
        failure_reason: str,
        exception: Optional[Exception] = None,
    ) -> str:
        """Send a failed message to the dead letter queue."""
        try:
            # Create DLQ message
            dlq_message = Message(
                topic=self._dlq_topic,
                key=message.key,
                value={
                    "original_topic": original_topic,
                    "original_message": message.dict(),
                    "failure_reason": failure_reason,
                    "exception_type": type(exception).__name__
                    if exception
                    else "Unknown",
                    "exception_message": str(exception) if exception else "",
                    "stack_trace": self._get_stack_trace(exception)
                    if exception
                    else None,
                    "retry_count": message.metadata.retry_count,
                    "max_retries": message.metadata.max_retries,
                    "next_retry_at": self._calculate_next_retry(
                        message.metadata.retry_count
                    ),
                    "retry_delay_seconds": self._calculate_retry_delay(
                        message.metadata.retry_count
                    ),
                    "dlq_timestamp": datetime.utcnow().isoformat(),
                },
                metadata=MessageMetadata(
                    message_id=f"dlq_{message.metadata.message_id}",
                    headers={
                        "original_topic": original_topic,
                        "original_message_id": message.metadata.message_id,
                        "failure_reason": failure_reason,
                    },
                ),
            )

            # Send to DLQ
            producer = await self._mq.get_producer()
            dlq_message_id = await producer.send_message(
                topic=self._dlq_topic,
                value=dlq_message.value,
                key=dlq_message.key,
                headers=dlq_message.metadata.headers,
                metadata=dlq_message.metadata,
            )

            self.logger.info(
                f"Sent message {message.metadata.message_id} to DLQ: {dlq_message_id}"
            )
            return dlq_message_id

        except Exception as e:
            self.logger.error(f"Error sending message to DLQ: {e}")
            raise

    async def start_retry_processor(self) -> None:
        """Start the retry processor."""
        if self._is_processing:
            return

        self._is_processing = True
        self._processing_task = asyncio.create_task(self._process_dlq_messages())
        self.logger.info("Started DLQ retry processor")

    async def stop_retry_processor(self) -> None:
        """Stop the retry processor."""
        if not self._is_processing:
            return

        self._is_processing = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Stopped DLQ retry processor")

    async def _process_dlq_messages(self) -> None:
        """Process messages from the DLQ."""
        consumer_config = ConsumerConfig(
            group_id="dlq-retry-processor", auto_offset_reset="latest"
        )

        consumer = await self._mq.get_consumer(consumer_config)
        await consumer.subscribe([self._dlq_topic], consumer_config)

        while self._is_processing:
            try:
                messages = await consumer.poll(timeout_ms=1000)

                for message in messages:
                    await self._process_dlq_message(message)

            except Exception as e:
                self.logger.error(f"Error processing DLQ messages: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _process_dlq_message(self, dlq_message: Message) -> None:
        """Process a single DLQ message."""
        try:
            dlq_data = dlq_message.value
            original_message = Message(**dlq_data["original_message"])

            # Check if we should retry
            if dlq_data["retry_count"] >= dlq_data["max_retries"]:
                self.logger.warning(
                    f"Message {original_message.metadata.message_id} exceeded max retries"
                )
                return

            # Check if it's time to retry
            next_retry = datetime.fromisoformat(dlq_data["next_retry_at"])
            if datetime.utcnow() < next_retry:
                return  # Not time to retry yet

            # Send to retry topic
            await self._send_to_retry_topic(original_message, dlq_data)

        except Exception as e:
            self.logger.error(f"Error processing DLQ message: {e}")

    async def _send_to_retry_topic(
        self, original_message: Message, dlq_data: Dict[str, Any]
    ) -> None:
        """Send a message to the retry topic."""
        try:
            # Update retry count
            original_message.metadata.retry_count = dlq_data["retry_count"] + 1

            # Send to retry topic
            producer = await self._mq.get_producer()
            await producer.send_message(
                topic=self._retry_topic,
                value=original_message.value,
                key=original_message.key,
                headers=original_message.metadata.headers,
                metadata=original_message.metadata,
            )

            self.logger.info(
                f"Sent message {original_message.metadata.message_id} to retry topic"
            )

        except Exception as e:
            self.logger.error(f"Error sending message to retry topic: {e}")

    def _calculate_next_retry(self, retry_count: int) -> str:
        """Calculate when to retry next."""
        delay = self._calculate_retry_delay(retry_count)
        next_retry = datetime.utcnow() + timedelta(seconds=delay)
        return next_retry.isoformat()

    def _calculate_retry_delay(self, retry_count: int) -> int:
        """Calculate retry delay with exponential backoff."""
        delay = min(self._base_retry_delay * (2**retry_count), self._max_retry_delay)
        return delay

    def _get_stack_trace(self, exception: Optional[Exception]) -> Optional[str]:
        """Get stack trace from exception."""
        if exception is None:
            return None

        import traceback

        return traceback.format_exc()

    async def get_dlq_metrics(self) -> Dict[str, Any]:
        """Get DLQ metrics."""
        try:
            # This would typically query the message queue for metrics
            # For now, return basic status
            return {
                "is_processing": self._is_processing,
                "dlq_topic": self._dlq_topic,
                "retry_topic": self._retry_topic,
                "max_retries": self._max_retries,
                "base_retry_delay": self._base_retry_delay,
                "max_retry_delay": self._max_retry_delay,
            }
        except Exception as e:
            self.logger.error(f"Error getting DLQ metrics: {e}")
            return {}

    async def manual_retry(self, dlq_message_id: str) -> bool:
        """Manually retry a DLQ message."""
        try:
            # This would typically fetch the specific DLQ message and retry it
            # Implementation depends on the specific message queue backend
            self.logger.info(
                f"Manual retry requested for DLQ message: {dlq_message_id}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Error manually retrying DLQ message {dlq_message_id}: {e}"
            )
            return False

    async def close(self) -> None:
        """Close the DLQ service."""
        await self.stop_retry_processor()
