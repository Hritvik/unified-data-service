"""
In-memory raw store implementation using deque for efficient sliding windows.
"""

import time
from collections import deque
from typing import List, Optional

from common_utils.logger import get_logger

from ..interfaces import IRawStore
from ..models import KPIPoint

logger = get_logger(__name__)


class InMemoryRawStore(IRawStore):
    """In-memory raw store using deque for efficient sliding window operations."""

    def __init__(
        self, max_samples: Optional[int] = None, ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Initialize in-memory raw store.

        Args:
            max_samples: Maximum number of samples to retain per metric
            ttl_seconds: Time to live in seconds for samples
        """
        self._storage: dict[str, deque[KPIPoint]] = {}
        self.max_samples = max_samples
        self.ttl_seconds = ttl_seconds

    async def add_sample(self, metric_id: str, point: KPIPoint) -> None:
        """Add a sample to the raw store."""
        if metric_id not in self._storage:
            self._storage[metric_id] = deque()

        samples = self._storage[metric_id]
        samples.append(point)

        # Enforce max_samples limit
        if self.max_samples and len(samples) > self.max_samples:
            samples.popleft()

        # Clean up expired samples if TTL is set
        if self.ttl_seconds:
            await self.cleanup_expired(metric_id)

    async def get_samples(
        self,
        metric_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[KPIPoint]:
        """Get samples for a metric within a time range."""
        if metric_id not in self._storage:
            return []

        samples = list(self._storage[metric_id])

        # Filter by time range
        if start_time is not None:
            samples = [s for s in samples if s.timestamp >= start_time]
        if end_time is not None:
            samples = [s for s in samples if s.timestamp <= end_time]

        return samples

    async def get_sample_count(self, metric_id: str) -> int:
        """Get the number of samples for a metric."""
        if metric_id not in self._storage:
            return 0
        return len(self._storage[metric_id])

    async def cleanup_expired(self, metric_id: str) -> int:
        """Clean up expired samples for a metric. Returns number of items cleaned."""
        if metric_id not in self._storage or not self.ttl_seconds:
            return 0

        samples = self._storage[metric_id]
        current_time = time.time()
        initial_count = len(samples)

        # Remove expired samples from the front (oldest first)
        while samples and (current_time - samples[0].timestamp) > self.ttl_seconds:
            samples.popleft()

        cleaned = initial_count - len(samples)
        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} expired samples for metric {metric_id}")

        return cleaned

    async def clear(self, metric_id: str) -> None:
        """Clear all samples for a metric."""
        if metric_id in self._storage:
            del self._storage[metric_id]
