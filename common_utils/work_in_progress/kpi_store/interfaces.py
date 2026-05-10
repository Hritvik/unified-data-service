"""
Core interfaces for the KPI store system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import KPIPoint, KPIValue


class IRawStore(ABC):
    """Interface for raw KPI storage (time-series samples)."""

    @abstractmethod
    async def add_sample(self, metric_id: str, point: KPIPoint) -> None:
        """Add a sample to the raw store."""
        pass

    @abstractmethod
    async def get_samples(
        self,
        metric_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[KPIPoint]:
        """Get samples for a KPI within a time range."""
        pass

    @abstractmethod
    async def get_sample_count(self, metric_id: str) -> int:
        """Get the number of samples for a KPI."""
        pass

    @abstractmethod
    async def cleanup_expired(self, metric_id: str) -> int:
        """Clean up expired samples for a KPI. Returns number of items cleaned."""
        pass

    @abstractmethod
    async def clear(self, metric_id: str) -> None:
        """Clear all samples for a KPI."""
        pass


class IFinalStore(ABC):
    """Interface for final (aggregated) KPI storage."""

    @abstractmethod
    async def set_metric_value(self, metric_id: str, value: KPIValue) -> None:
        """Set the value for a KPI."""
        pass

    @abstractmethod
    async def get_metric_value(
        self, metric_id: str, window_name: Optional[str] = None
    ) -> Optional[KPIValue]:
        """Get the value for a KPI."""
        pass

    @abstractmethod
    async def delete_metric(self, metric_id: str) -> None:
        """Delete a KPI from the store."""
        pass

    @abstractmethod
    async def list_metrics(self) -> List[str]:
        """List all KPI IDs in the store."""
        pass


class IKPIAlgorithm(ABC):
    """Interface for KPI computation algorithms."""

    @abstractmethod
    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """
        Compute KPI value from samples.

        Args:
            samples: List of KPI points
            previous_value: Previous computed value (for incremental algorithms)

        Returns:
            Computed KPI value
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        pass


class IKPIStore(ABC):
    """Main interface for the KPI store system."""

    @abstractmethod
    async def register_metric(self, definition: Any) -> None:
        """Register a KPI definition."""
        pass

    @abstractmethod
    async def register_derived_metric(self, definition: Any) -> None:
        """Register a derived KPI definition."""
        pass

    @abstractmethod
    async def record_metric(
        self, metric_id: str, value: float, timestamp: Optional[float] = None
    ) -> None:
        """Record a KPI value."""
        pass

    @abstractmethod
    async def record_metrics_batch(self, metrics: Dict[str, Any]) -> Any:
        """Record multiple KPIs in a batch."""
        pass

    @abstractmethod
    async def get_metric_value(
        self, metric_id: str, window_name: Optional[str] = None
    ) -> Optional[KPIValue]:
        """Get the current value of a KPI."""
        pass

    @abstractmethod
    async def list_metrics(self) -> List[str]:
        """List all registered KPIs."""
        pass

    @abstractmethod
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check."""
        pass

    @abstractmethod
    async def cleanup_expired_metrics(self) -> Any:
        """Clean up expired KPIs."""
        pass

    @abstractmethod
    async def export_metrics(
        self, metric_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Export KPI data."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the KPI store."""
        pass
