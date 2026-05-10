"""
In-memory final store implementation using dict for fast access.
"""

from typing import Dict, List, Optional

from common_utils.logger import get_logger

from ..interfaces import IFinalStore
from ..models import KPIValue

logger = get_logger(__name__)


class InMemoryFinalStore(IFinalStore):
    """In-memory final store using dict for fast access."""

    def __init__(self) -> None:
        """Initialize in-memory final store."""
        # Store format: {metric_id: {window_name: KPIValue}}
        self._storage: Dict[str, Dict[str, KPIValue]] = {}

    async def set_metric_value(self, metric_id: str, value: KPIValue) -> None:
        """Set the value for a metric."""
        if metric_id not in self._storage:
            self._storage[metric_id] = {}

        window_key = value.window_name or "default"
        self._storage[metric_id][window_key] = value

    async def get_metric_value(
        self, metric_id: str, window_name: Optional[str] = None
    ) -> Optional[KPIValue]:
        """Get the value for a metric."""
        if metric_id not in self._storage:
            return None

        window_key = window_name or "default"
        return self._storage[metric_id].get(window_key)

    async def delete_metric(self, metric_id: str) -> None:
        """Delete a metric from the store."""
        if metric_id in self._storage:
            del self._storage[metric_id]

    async def list_metrics(self) -> List[str]:
        """List all metric IDs in the store."""
        return list(self._storage.keys())
