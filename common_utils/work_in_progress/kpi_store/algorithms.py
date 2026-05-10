"""
Computation algorithms for KPIs.
"""

import math
from typing import Any, Callable, Dict, List, Optional

from common_utils.logger import get_logger

from .enums import Algorithm
from .interfaces import IKPIAlgorithm
from .models import KPIPoint

logger = get_logger(__name__)


class CounterAlgorithm(IKPIAlgorithm):
    """Simple counter algorithm that sums all values."""

    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """Compute sum of all sample values."""
        if not samples:
            return previous_value or 0.0
        return sum(point.value for point in samples)

    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        return {}


class GaugeAlgorithm(IKPIAlgorithm):
    """Gauge algorithm that returns the latest value."""

    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """Return the latest sample value."""
        if not samples:
            return previous_value or 0.0
        # Return the most recent value (last in list)
        return samples[-1].value

    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        return {}


class SimpleAverageAlgorithm(IKPIAlgorithm):
    """Simple arithmetic mean algorithm."""

    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """Compute arithmetic mean of all sample values."""
        if not samples:
            return previous_value or 0.0
        values = [point.value for point in samples]
        return sum(values) / len(values)

    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        return {}


class EWMAAlgorithm(IKPIAlgorithm):
    """Exponentially Weighted Moving Average algorithm."""

    def __init__(self, alpha: float = 0.1) -> None:
        """
        Initialize EWMA algorithm.

        Args:
            alpha: Smoothing factor (0 < alpha <= 1). Higher values give more weight to recent data.
        """
        if not 0 < alpha <= 1:
            raise ValueError("Alpha must be between 0 and 1")
        self.alpha = alpha

    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """
        Compute exponentially weighted moving average.

        Formula: new_value = alpha * current_value + (1 - alpha) * previous_value
        """
        if not samples:
            return previous_value or 0.0

        if previous_value is None:
            # Initialize with first value
            return samples[0].value

        # Apply EWMA to all samples
        result = previous_value
        for point in samples:
            result = self.alpha * point.value + (1 - self.alpha) * result

        return result

    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        return {"alpha": self.alpha}


class WelfordAlgorithm(IKPIAlgorithm):
    """Welford's online algorithm for computing mean and variance."""

    def __init__(self, return_type: str = "mean") -> None:
        """
        Initialize Welford algorithm.

        Args:
            return_type: What to return - "mean", "variance", or "stddev"
        """
        if return_type not in ["mean", "variance", "stddev"]:
            raise ValueError("return_type must be 'mean', 'variance', or 'stddev'")
        self.return_type = return_type

    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """
        Compute mean, variance, or standard deviation using Welford's algorithm.

        This is an online algorithm that can compute statistics incrementally.
        """
        if not samples:
            return previous_value or 0.0

        values = [point.value for point in samples]
        n = len(values)

        # Welford's algorithm
        mean = 0.0
        m2 = 0.0  # Sum of squared differences

        for i, value in enumerate(values, 1):
            delta = value - mean
            mean += delta / i
            delta2 = value - mean
            m2 += delta * delta2

        if self.return_type == "mean":
            return mean
        elif self.return_type == "variance":
            return m2 / n if n > 0 else 0.0
        else:  # stddev
            variance = m2 / n if n > 0 else 0.0
            return math.sqrt(variance)

    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        return {"return_type": self.return_type}


class CustomAlgorithm(IKPIAlgorithm):
    """Wrapper for custom algorithm functions."""

    def __init__(
        self, compute_func: Callable[[List[KPIPoint], Optional[float]], float]
    ) -> None:
        """
        Initialize custom algorithm.

        Args:
            compute_func: Function that takes samples and previous value, returns computed value
        """
        self.compute_func = compute_func
        self._parameters: Dict[str, Any] = {}

    async def compute(
        self, samples: List[KPIPoint], previous_value: Optional[float] = None
    ) -> float:
        """Compute using the custom function."""
        try:
            # Handle both sync and async functions
            if hasattr(self.compute_func, "__call__"):
                result = self.compute_func(samples, previous_value)
                # If it's a coroutine, await it
                if hasattr(result, "__await__"):
                    return await result
                return result
            return previous_value or 0.0
        except Exception as e:
            logger.error(f"Error in custom algorithm: {e}")
            return previous_value or 0.0

    def get_parameters(self) -> Dict[str, Any]:
        """Get algorithm parameters."""
        return self._parameters

    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set algorithm parameters."""
        self._parameters = parameters


# Algorithm registry
_ALGORITHM_REGISTRY: Dict[Algorithm, type[IKPIAlgorithm]] = {
    Algorithm.COUNTER: CounterAlgorithm,
    Algorithm.GAUGE: GaugeAlgorithm,
    Algorithm.SIMPLE_AVERAGE: SimpleAverageAlgorithm,
    Algorithm.EWMA: EWMAAlgorithm,
    Algorithm.WELFORD: WelfordAlgorithm,
}


def create_algorithm(
    algorithm: Algorithm, parameters: Optional[Dict[str, Any]] = None
) -> IKPIAlgorithm:
    """
    Create an algorithm instance.

    Args:
        algorithm: Algorithm type
        parameters: Algorithm-specific parameters

    Returns:
        Algorithm instance
    """
    if algorithm == Algorithm.CUSTOM:
        raise ValueError("Use CustomAlgorithm class directly for custom algorithms")

    if algorithm not in _ALGORITHM_REGISTRY:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    algorithm_class = _ALGORITHM_REGISTRY[algorithm]
    parameters = parameters or {}

    # Special handling for algorithms that need parameters
    if algorithm == Algorithm.EWMA:
        alpha = parameters.get("alpha", 0.1)
        return algorithm_class(alpha=alpha)
    elif algorithm == Algorithm.WELFORD:
        return_type = parameters.get("return_type", "mean")
        return algorithm_class(return_type=return_type)
    else:
        return algorithm_class()
