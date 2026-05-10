"""
Redis raw store implementation using ZSET for timestamped events.
"""

import json
import time
from typing import List, Optional

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from ..interfaces import IRawStore
from ..models import KPIPoint

logger = get_logger(__name__)


class RedisRawStore(IRawStore):
    """Redis raw store using ZSET for timestamped events with automatic expiry."""

    def __init__(
        self,
        redis_client: RedisClient,
        key_prefix: str = "metrics:raw:",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Initialize Redis raw store.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis keys
            ttl_seconds: Time to live in seconds for keys
        """
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds

    def _get_key(self, metric_id: str) -> str:
        """Get Redis key for a metric."""
        return f"{self.key_prefix}{metric_id}"

    async def add_sample(self, metric_id: str, point: KPIPoint) -> None:
        """Add a sample to the raw store."""
        key = self._get_key(metric_id)
        # Use timestamp as score and value as JSON
        value = json.dumps({"value": point.value, "timestamp": point.timestamp})
        score = point.timestamp

        await self.redis_client.zadd(key, {value: score})

        # Set TTL if configured
        if self.ttl_seconds:
            await self.redis_client.expire(key, self.ttl_seconds)

    async def get_samples(
        self,
        metric_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[KPIPoint]:
        """Get samples for a metric within a time range."""
        key = self._get_key(metric_id)

        # Use ZRANGEBYSCORE to get samples in time range
        if start_time is not None and end_time is not None:
            values = await self.redis_client.zrangebyscore(key, start_time, end_time)
        elif start_time is not None:
            values = await self.redis_client.zrangebyscore(key, start_time, "+inf")
        elif end_time is not None:
            values = await self.redis_client.zrangebyscore(key, "-inf", end_time)
        else:
            values = await self.redis_client.zrange(key, 0, -1)

        # Parse JSON values back to KPIPoint
        samples = []
        for value in values:
            try:
                data = json.loads(value)
                samples.append(
                    KPIPoint(timestamp=data["timestamp"], value=data["value"])
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing sample value: {e}")
                continue

        return samples

    async def get_sample_count(self, metric_id: str) -> int:
        """Get the number of samples for a metric."""
        key = self._get_key(metric_id)
        count = await self.redis_client.zcard(key)
        return count or 0

    async def cleanup_expired(self, metric_id: str) -> int:
        """Clean up expired samples for a metric. Returns number of items cleaned."""
        if not self.ttl_seconds:
            return 0

        key = self._get_key(metric_id)
        current_time = time.time()
        cutoff_time = current_time - self.ttl_seconds

        # Remove samples older than TTL
        removed = await self.redis_client.zremrangebyscore(key, "-inf", cutoff_time)
        return removed or 0

    async def clear(self, metric_id: str) -> None:
        """Clear all samples for a metric."""
        key = self._get_key(metric_id)
        await self.redis_client.delete(key)
