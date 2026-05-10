"""
Redis final store implementation using HASH for structured storage.
"""

import json
from typing import List, Optional

from common_utils.logger import get_logger
from common_utils.redis_client import RedisClient

from ..interfaces import IFinalStore
from ..models import KPIValue

logger = get_logger(__name__)


class RedisFinalStore(IFinalStore):
    """Redis final store using HASH for structured storage."""

    def __init__(
        self,
        redis_client: RedisClient,
        key_prefix: str = "metrics:final:",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Initialize Redis final store.

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

    def _get_field_key(self, window_name: Optional[str] = None) -> str:
        """Get field key within a hash for a window."""
        return window_name or "default"

    async def set_metric_value(self, metric_id: str, value: KPIValue) -> None:
        """Set the value for a metric."""
        key = self._get_key(metric_id)
        field = self._get_field_key(value.window_name)

        # Store as JSON
        value_dict = value.model_dump()
        value_json = json.dumps(value_dict)

        await self.redis_client.hset(key, field, value_json)

        # Set TTL if configured
        if self.ttl_seconds:
            await self.redis_client.expire(key, self.ttl_seconds)

    async def get_metric_value(
        self, metric_id: str, window_name: Optional[str] = None
    ) -> Optional[KPIValue]:
        """Get the value for a metric."""
        key = self._get_key(metric_id)
        field = self._get_field_key(window_name)

        value_json = await self.redis_client.hget(key, field)
        if not value_json:
            return None

        try:
            value_dict = json.loads(value_json)
            return KPIValue(**value_dict)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing metric value: {e}")
            return None

    async def delete_metric(self, metric_id: str) -> None:
        """Delete a metric from the store."""
        key = self._get_key(metric_id)
        await self.redis_client.delete(key)

    async def list_metrics(self) -> List[str]:
        """List all metric IDs in the store."""
        # Get all keys matching the prefix
        pattern = f"{self.key_prefix}*"
        keys = await self.redis_client.keys(pattern)

        # Remove prefix to get metric IDs
        prefix_len = len(self.key_prefix)
        return [key[prefix_len:] for key in keys]
