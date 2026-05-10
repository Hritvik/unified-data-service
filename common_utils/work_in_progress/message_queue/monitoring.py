"""
Message Queue Monitoring and Metrics.

This module provides monitoring capabilities and metrics collection
for message queue operations.
"""

import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List

from common_utils.logger import get_logger

logger = get_logger(__name__)


class MessageQueueMetrics:
    """Collects and manages metrics for message queue operations."""

    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "dlq_messages": 0,
            "retry_attempts": 0,
            "processing_times": [],
            "error_counts": {},
            "topic_metrics": {},
            "start_time": datetime.utcnow(),
        }
        self._operation_times: Dict[str, List[float]] = {}
        self.logger = logger

    def increment_messages_sent(self, topic: str = "unknown", count: int = 1) -> None:
        """Increment sent messages counter."""
        self._metrics["messages_sent"] += count

        if topic not in self._metrics["topic_metrics"]:
            self._metrics["topic_metrics"][topic] = {
                "sent": 0,
                "received": 0,
                "failed": 0,
            }
        self._metrics["topic_metrics"][topic]["sent"] += count

    def increment_messages_received(
        self, topic: str = "unknown", count: int = 1
    ) -> None:
        """Increment received messages counter."""
        self._metrics["messages_received"] += count

        if topic not in self._metrics["topic_metrics"]:
            self._metrics["topic_metrics"][topic] = {
                "sent": 0,
                "received": 0,
                "failed": 0,
            }
        self._metrics["topic_metrics"][topic]["received"] += count

    def increment_messages_failed(
        self, topic: str = "unknown", error_type: str = "unknown", count: int = 1
    ) -> None:
        """Increment failed messages counter."""
        self._metrics["messages_failed"] += count

        if topic not in self._metrics["topic_metrics"]:
            self._metrics["topic_metrics"][topic] = {
                "sent": 0,
                "received": 0,
                "failed": 0,
            }
        self._metrics["topic_metrics"][topic]["failed"] += count

        if error_type not in self._metrics["error_counts"]:
            self._metrics["error_counts"][error_type] = 0
        self._metrics["error_counts"][error_type] += count

    def increment_dlq_messages(self, count: int = 1) -> None:
        """Increment DLQ messages counter."""
        self._metrics["dlq_messages"] += count

    def increment_retry_attempts(self, count: int = 1) -> None:
        """Increment retry attempts counter."""
        self._metrics["retry_attempts"] += count

    def record_processing_time(self, operation: str, duration_seconds: float) -> None:
        """Record processing time for an operation."""
        self._metrics["processing_times"].append(duration_seconds)

        if operation not in self._operation_times:
            self._operation_times[operation] = []
        self._operation_times[operation].append(duration_seconds)

        # Keep only last 1000 entries to prevent memory growth
        if len(self._metrics["processing_times"]) > 1000:
            self._metrics["processing_times"] = self._metrics["processing_times"][
                -1000:
            ]

        if len(self._operation_times[operation]) > 1000:
            self._operation_times[operation] = self._operation_times[operation][-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        current_time = datetime.utcnow()
        uptime = current_time - self._metrics["start_time"]

        # Calculate averages
        avg_processing_time = 0.0
        if self._metrics["processing_times"]:
            avg_processing_time = sum(self._metrics["processing_times"]) / len(
                self._metrics["processing_times"]
            )

        # Calculate rates (per minute)
        uptime_minutes = max(uptime.total_seconds() / 60, 1)  # Avoid division by zero

        metrics = {
            **self._metrics,
            "uptime_seconds": uptime.total_seconds(),
            "avg_processing_time_seconds": avg_processing_time,
            "messages_sent_per_minute": self._metrics["messages_sent"] / uptime_minutes,
            "messages_received_per_minute": self._metrics["messages_received"]
            / uptime_minutes,
            "messages_failed_per_minute": self._metrics["messages_failed"]
            / uptime_minutes,
            "success_rate": self._calculate_success_rate(),
            "operation_metrics": self._get_operation_metrics(),
            "timestamp": current_time.isoformat(),
        }

        return metrics

    def _calculate_success_rate(self) -> float:
        """Calculate message success rate."""
        total_messages = (
            self._metrics["messages_sent"] + self._metrics["messages_received"]
        )
        if total_messages == 0:
            return 1.0

        successful_messages = total_messages - self._metrics["messages_failed"]
        return successful_messages / total_messages

    def _get_operation_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get metrics for specific operations."""
        operation_metrics = {}

        for operation, times in self._operation_times.items():
            if times:
                operation_metrics[operation] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                }

        return operation_metrics

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "dlq_messages": 0,
            "retry_attempts": 0,
            "processing_times": [],
            "error_counts": {},
            "topic_metrics": {},
            "start_time": datetime.utcnow(),
        }
        self._operation_times = {}
        self.logger.info("Message queue metrics reset")


# Global metrics instance
message_queue_metrics = MessageQueueMetrics()


def track_message_operation(operation_name: str = "message_operation"):
    """Decorator to track message queue operations."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                message_queue_metrics.record_processing_time(operation_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                message_queue_metrics.record_processing_time(
                    f"{operation_name}_failed", duration
                )
                message_queue_metrics.increment_messages_failed(
                    error_type=type(e).__name__
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                message_queue_metrics.record_processing_time(operation_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                message_queue_metrics.record_processing_time(
                    f"{operation_name}_failed", duration
                )
                message_queue_metrics.increment_messages_failed(
                    error_type=type(e).__name__
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class MessageQueueHealthChecker:
    """Health checker for message queue operations."""

    def __init__(self, metrics: MessageQueueMetrics):
        self._metrics = metrics
        self.logger = logger

    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        metrics = self._metrics.get_metrics()

        health_status = {
            "status": "healthy",
            "checks": {},
            "metrics_summary": {
                "total_messages": metrics["messages_sent"]
                + metrics["messages_received"],
                "success_rate": metrics["success_rate"],
                "avg_processing_time": metrics["avg_processing_time_seconds"],
                "uptime_seconds": metrics["uptime_seconds"],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Check success rate
        if metrics["success_rate"] < 0.95:  # Less than 95% success rate
            health_status["checks"]["success_rate"] = {
                "status": "warning",
                "message": f"Success rate is {metrics['success_rate']:.2%}",
                "value": metrics["success_rate"],
            }
            health_status["status"] = "warning"
        else:
            health_status["checks"]["success_rate"] = {
                "status": "healthy",
                "message": f"Success rate is {metrics['success_rate']:.2%}",
                "value": metrics["success_rate"],
            }

        # Check processing time
        if metrics["avg_processing_time_seconds"] > 5.0:  # More than 5 seconds average
            health_status["checks"]["processing_time"] = {
                "status": "warning",
                "message": f"Average processing time is {metrics['avg_processing_time_seconds']:.2f}s",
                "value": metrics["avg_processing_time_seconds"],
            }
            health_status["status"] = "warning"
        else:
            health_status["checks"]["processing_time"] = {
                "status": "healthy",
                "message": f"Average processing time is {metrics['avg_processing_time_seconds']:.2f}s",
                "value": metrics["avg_processing_time_seconds"],
            }

        # Check error rate
        total_messages = metrics["messages_sent"] + metrics["messages_received"]
        if total_messages > 0:
            error_rate = metrics["messages_failed"] / total_messages
            if error_rate > 0.05:  # More than 5% error rate
                health_status["checks"]["error_rate"] = {
                    "status": "warning",
                    "message": f"Error rate is {error_rate:.2%}",
                    "value": error_rate,
                }
                health_status["status"] = "warning"
            else:
                health_status["checks"]["error_rate"] = {
                    "status": "healthy",
                    "message": f"Error rate is {error_rate:.2%}",
                    "value": error_rate,
                }

        # Check DLQ messages
        if metrics["dlq_messages"] > 100:  # More than 100 DLQ messages
            health_status["checks"]["dlq_messages"] = {
                "status": "warning",
                "message": f"High number of DLQ messages: {metrics['dlq_messages']}",
                "value": metrics["dlq_messages"],
            }
            health_status["status"] = "warning"
        else:
            health_status["checks"]["dlq_messages"] = {
                "status": "healthy",
                "message": f"DLQ messages: {metrics['dlq_messages']}",
                "value": metrics["dlq_messages"],
            }

        return health_status

    def get_alert_conditions(self) -> List[Dict[str, Any]]:
        """Get current alert conditions."""
        metrics = self._metrics.get_metrics()
        alerts = []

        # High error rate alert
        total_messages = metrics["messages_sent"] + metrics["messages_received"]
        if total_messages > 0:
            error_rate = metrics["messages_failed"] / total_messages
            if error_rate > 0.1:  # More than 10% error rate
                alerts.append(
                    {
                        "type": "high_error_rate",
                        "severity": "critical",
                        "message": f"Error rate is {error_rate:.2%}",
                        "value": error_rate,
                        "threshold": 0.1,
                    }
                )

        # High processing time alert
        if metrics["avg_processing_time_seconds"] > 10.0:  # More than 10 seconds
            alerts.append(
                {
                    "type": "high_processing_time",
                    "severity": "warning",
                    "message": f"Average processing time is {metrics['avg_processing_time_seconds']:.2f}s",
                    "value": metrics["avg_processing_time_seconds"],
                    "threshold": 10.0,
                }
            )

        # High DLQ messages alert
        if metrics["dlq_messages"] > 500:  # More than 500 DLQ messages
            alerts.append(
                {
                    "type": "high_dlq_messages",
                    "severity": "critical",
                    "message": f"High number of DLQ messages: {metrics['dlq_messages']}",
                    "value": metrics["dlq_messages"],
                    "threshold": 500,
                }
            )

        return alerts


# Global health checker instance
message_queue_health_checker = MessageQueueHealthChecker(message_queue_metrics)
