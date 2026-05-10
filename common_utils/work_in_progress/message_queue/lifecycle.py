"""
Message Queue Lifecycle Management.

This module provides lifecycle management for message queue operations,
including startup, shutdown, and health checks.
"""

import asyncio
from typing import Any, Dict

from common_utils.logger import get_logger

from .dlq_service import DeadLetterQueueService
from .interfaces import IMessageQueue

logger = get_logger(__name__)


class MessageQueueLifecycleManager:
    """Manages the lifecycle of message queue services."""

    def __init__(self):
        self._message_queues: Dict[str, IMessageQueue] = {}
        self._dlq_services: Dict[str, DeadLetterQueueService] = {}
        self._is_started = False
        self.logger = logger

    async def register_message_queue(
        self, name: str, message_queue: IMessageQueue
    ) -> None:
        """Register a message queue instance."""
        if name in self._message_queues:
            self.logger.warning(f"Message queue '{name}' is already registered")
            return

        self._message_queues[name] = message_queue
        self.logger.info(f"Registered message queue: {name}")

    async def register_dlq_service(
        self, name: str, dlq_service: DeadLetterQueueService
    ) -> None:
        """Register a DLQ service instance."""
        if name in self._dlq_services:
            self.logger.warning(f"DLQ service '{name}' is already registered")
            return

        self._dlq_services[name] = dlq_service
        self.logger.info(f"Registered DLQ service: {name}")

    async def start_all(self) -> None:
        """Start all registered message queue services."""
        if self._is_started:
            self.logger.warning("Message queue services are already started")
            return

        try:
            # Start all DLQ services
            for name, dlq_service in self._dlq_services.items():
                try:
                    await dlq_service.start_retry_processor()
                    self.logger.info(f"Started DLQ service: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to start DLQ service '{name}': {e}")
                    raise

            self._is_started = True
            self.logger.info("All message queue services started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start message queue services: {e}")
            # Attempt to stop any services that were started
            await self.stop_all()
            raise

    async def stop_all(self) -> None:
        """Stop all registered message queue services."""
        if not self._is_started:
            self.logger.info("Message queue services are not started")
            return

        # Stop all DLQ services
        for name, dlq_service in self._dlq_services.items():
            try:
                await dlq_service.stop_retry_processor()
                self.logger.info(f"Stopped DLQ service: {name}")
            except Exception as e:
                self.logger.error(f"Error stopping DLQ service '{name}': {e}")

        # Close all message queues
        for name, message_queue in self._message_queues.items():
            try:
                await message_queue.close()
                self.logger.info(f"Closed message queue: {name}")
            except Exception as e:
                self.logger.error(f"Error closing message queue '{name}': {e}")

        self._is_started = False
        self.logger.info("All message queue services stopped")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all message queue services."""
        health_status = {
            "status": "healthy",
            "is_started": self._is_started,
            "message_queues": {},
            "dlq_services": {},
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Check message queues
        for name, message_queue in self._message_queues.items():
            try:
                # Basic health check - try to get queue info
                info = await message_queue.get_queue_info("health-check")
                health_status["message_queues"][name] = {
                    "status": "healthy",
                    "info": info,
                }
            except Exception as e:
                health_status["message_queues"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["status"] = "unhealthy"

        # Check DLQ services
        for name, dlq_service in self._dlq_services.items():
            try:
                metrics = await dlq_service.get_dlq_metrics()
                health_status["dlq_services"][name] = {
                    "status": "healthy",
                    "metrics": metrics,
                }
            except Exception as e:
                health_status["dlq_services"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["status"] = "unhealthy"

        return health_status

    async def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for all message queue services."""
        metrics = {
            "message_queues": len(self._message_queues),
            "dlq_services": len(self._dlq_services),
            "is_started": self._is_started,
            "services": {},
        }

        # Get DLQ service metrics
        for name, dlq_service in self._dlq_services.items():
            try:
                service_metrics = await dlq_service.get_dlq_metrics()
                metrics["services"][name] = service_metrics
            except Exception as e:
                self.logger.error(
                    f"Error getting metrics for DLQ service '{name}': {e}"
                )
                metrics["services"][name] = {"error": str(e)}

        return metrics

    def get_registered_services(self) -> Dict[str, Any]:
        """Get information about registered services."""
        return {
            "message_queues": list(self._message_queues.keys()),
            "dlq_services": list(self._dlq_services.keys()),
            "is_started": self._is_started,
        }

    async def restart_service(self, service_type: str, service_name: str) -> bool:
        """Restart a specific service."""
        try:
            if service_type == "dlq" and service_name in self._dlq_services:
                dlq_service = self._dlq_services[service_name]
                await dlq_service.stop_retry_processor()
                await dlq_service.start_retry_processor()
                self.logger.info(f"Restarted DLQ service: {service_name}")
                return True
            else:
                self.logger.error(
                    f"Unknown service type '{service_type}' or service '{service_name}'"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error restarting service '{service_name}': {e}")
            return False


# Global message queue lifecycle manager instance
message_queue_lifecycle = MessageQueueLifecycleManager()


# Lifecycle integration functions
async def startup_message_queue() -> None:
    """Startup function for message queue services."""
    try:
        await message_queue_lifecycle.start_all()
        logger.info("Message queue lifecycle started")
    except Exception as e:
        logger.error(f"Failed to start message queue lifecycle: {e}")
        raise


async def shutdown_message_queue() -> None:
    """Shutdown function for message queue services."""
    try:
        await message_queue_lifecycle.stop_all()
        logger.info("Message queue lifecycle stopped")
    except Exception as e:
        logger.error(f"Error during message queue lifecycle shutdown: {e}")


# Register with the global lifecycle manager
def register_message_queue_lifecycle() -> None:
    """Register message queue lifecycle with the global lifecycle manager."""
    try:
        from common_utils.lifecycle_manager import lifecycle_manager

        lifecycle_manager.register_module(
            name="message_queue",
            startup=startup_message_queue,
            shutdown=shutdown_message_queue,
            required=False,  # Message queue is optional by default
            dependencies=[],  # No dependencies by default
        )
        logger.info("Message queue lifecycle registered with global lifecycle manager")

    except ImportError:
        logger.warning(
            "Could not register message queue lifecycle - lifecycle_manager not available"
        )
    except Exception as e:
        logger.error(f"Error registering message queue lifecycle: {e}")
