"""
Derived metrics management with dependency resolution.
"""

import asyncio
from typing import Callable, Dict, List, Optional

from common_utils.logger import get_logger
from common_utils.task_dependency_utils import get_parallel_execution_batches

from .interfaces import IKPIStore
from .models import DerivedKPIDefinition, KPIValue

logger = get_logger(__name__)


class ComputationRegistry:
    """Registry for computation functions."""

    def __init__(self) -> None:
        """Initialize computation registry."""
        self._functions: Dict[str, Callable[[Dict[str, float]], float]] = {}
        self._register_builtin_functions()

    def _register_builtin_functions(self) -> None:
        """Register built-in computation functions."""
        # Success rate: successful / total
        self.register(
            "success_rate",
            lambda deps: deps.get("successful_requests", 0)
            / max(deps.get("total_requests", 1), 1),
        )

        # Error rate: 1 - success_rate
        self.register(
            "error_rate",
            lambda deps: 1.0
            - (
                deps.get("success_rate", 0)
                if "success_rate" in deps
                else (
                    deps.get("successful_requests", 0)
                    / max(deps.get("total_requests", 1), 1)
                )
            ),
        )

        # Percentage: numerator / denominator * 100
        self.register(
            "percentage",
            lambda deps: (deps.get("numerator", 0) / max(deps.get("denominator", 1), 1))
            * 100,
        )

        # Add: sum of all dependencies
        self.register("add", lambda deps: sum(deps.values()))

        # Subtract: first - second
        self.register(
            "subtract",
            lambda deps: list(deps.values())[0] - list(deps.values())[1]
            if len(deps) >= 2
            else 0.0,
        )

        # Multiply: product of all dependencies
        import math

        self.register(
            "multiply", lambda deps: math.prod(deps.values()) if deps else 1.0
        )

        # Divide: first / second
        self.register(
            "divide",
            lambda deps: list(deps.values())[0] / max(list(deps.values())[1], 1)
            if len(deps) >= 2
            else 0.0,
        )

        # Average: mean of all dependencies
        self.register(
            "average", lambda deps: sum(deps.values()) / len(deps) if deps else 0.0
        )

        # Min: minimum of all dependencies
        self.register("min", lambda deps: min(deps.values()) if deps else 0.0)

        # Max: maximum of all dependencies
        self.register("max", lambda deps: max(deps.values()) if deps else 0.0)

    def register(self, name: str, func: Callable[[Dict[str, float]], float]) -> None:
        """
        Register a computation function.

        Args:
            name: Name of the function
            func: Function that takes a dict of dependency values and returns computed value
        """
        self._functions[name] = func
        logger.debug(f"Registered computation function: {name}")

    def get(self, name: str) -> Optional[Callable[[Dict[str, float]], float]]:
        """Get a computation function by name."""
        return self._functions.get(name)

    def list_functions(self) -> List[str]:
        """List all registered function names."""
        return list(self._functions.keys())


class DerivedMetricsManager:
    """Manages derived metrics with dependency resolution."""

    def __init__(self, metric_store: IKPIStore, enable_parallel: bool = True) -> None:
        """
        Initialize derived metrics manager.

        Args:
            metric_store: Reference to the metric store
            enable_parallel: Enable parallel computation of independent metrics
        """
        self.metric_store = metric_store
        self.enable_parallel = enable_parallel
        self.computation_registry = ComputationRegistry()
        self._derived_metrics: Dict[str, DerivedKPIDefinition] = {}
        self._cache: Dict[str, KPIValue] = {}
        self.logger = logger

    def register_derived_metric(self, definition: DerivedKPIDefinition) -> None:
        """
        Register a derived metric.

        Args:
            definition: Derived metric definition
        """
        # Validate dependencies exist
        all_metrics = (
            self.metric_store.list_metrics()
            if hasattr(self.metric_store, "list_metrics")
            else []
        )
        missing_deps = [
            dep
            for dep in definition.dependencies
            if dep not in all_metrics and dep not in self._derived_metrics
        ]

        if missing_deps:
            raise ValueError(
                f"Missing dependencies for {definition.metric_id}: {missing_deps}"
            )

        # Check for circular dependencies
        self._check_circular_dependency(definition.metric_id, definition.dependencies)

        self._derived_metrics[definition.metric_id] = definition
        self.logger.info(f"Registered derived metric: {definition.metric_id}")

    def _check_circular_dependency(
        self, metric_id: str, dependencies: List[str]
    ) -> None:
        """Check for circular dependencies."""
        visited = set()

        def check_dep(dep_id: str, path: List[str]) -> None:
            if dep_id in path:
                raise ValueError(
                    f"Circular dependency detected: {' -> '.join(path + [dep_id])}"
                )

            if dep_id in visited:
                return

            visited.add(dep_id)

            if dep_id in self._derived_metrics:
                for sub_dep in self._derived_metrics[dep_id].dependencies:
                    check_dep(sub_dep, path + [dep_id])

        for dep in dependencies:
            check_dep(dep, [metric_id])

    async def compute_derived_metric(self, metric_id: str) -> Optional[KPIValue]:
        """
        Compute a derived metric value.

        Args:
            metric_id: ID of the derived metric

        Returns:
            Computed metric value or None if computation fails
        """
        if metric_id not in self._derived_metrics:
            return None

        definition = self._derived_metrics[metric_id]

        # Check cache first
        if metric_id in self._cache:
            cached_value = self._cache[metric_id]
            # Check if cache is still valid (simple TTL check - could be enhanced)
            return cached_value

        try:
            # Get dependency values
            dependency_values: Dict[str, float] = {}
            for dep_id in definition.dependencies:
                dep_value = await self.metric_store.get_metric_value(dep_id)
                if dep_value is None:
                    self.logger.warning(f"Missing dependency value for {dep_id}")
                    return None
                dependency_values[dep_id] = dep_value.value

            # Get computation function
            compute_func = self.computation_registry.get(
                definition.computation_function_name
            )
            if not compute_func:
                self.logger.error(
                    f"Unknown computation function: {definition.computation_function_name}"
                )
                return None

            # Compute value
            computed_value = compute_func(dependency_values)

            # Create metric value
            import time

            metric_value = KPIValue(
                metric_id=metric_id,
                value=computed_value,
                timestamp=time.time(),
                metadata={"dependencies": definition.dependencies},
            )

            # Cache the result
            self._cache[metric_id] = metric_value

            return metric_value

        except Exception as e:
            self.logger.error(f"Error computing derived metric {metric_id}: {e}")
            return None

    async def compute_all_derived_metrics(self) -> Dict[str, KPIValue]:
        """
        Compute all derived metrics in dependency order.

        Returns:
            Dict mapping metric IDs to computed values
        """
        if not self._derived_metrics:
            return {}

        # Get dependency order using topological sort
        try:
            # Create task-like objects for sorting
            class DerivedMetricTask:  # noqa: B903
                def __init__(self, metric_id: str, dependencies: List[str]) -> None:
                    self.id = metric_id
                    self.dependencies = dependencies

            tasks = [
                DerivedMetricTask(metric_id, definition.dependencies)
                for metric_id, definition in self._derived_metrics.items()
            ]

            if self.enable_parallel:
                # Get parallel execution batches
                batches = get_parallel_execution_batches(tasks)

                results: Dict[str, KPIValue] = {}
                for batch in batches:
                    # Compute metrics in this batch in parallel
                    batch_results = await asyncio.gather(
                        *[self.compute_derived_metric(task.id) for task in batch],
                        return_exceptions=True,
                    )

                    for task, result in zip(batch, batch_results):
                        if isinstance(result, Exception):
                            self.logger.error(f"Error computing {task.id}: {result}")
                        elif result:
                            results[task.id] = result

                return results
            else:
                # Sequential computation
                from common_utils.task_dependency_utils import (
                    sort_tasks_by_dependencies,
                )

                sorted_tasks = sort_tasks_by_dependencies(tasks)

                results: Dict[str, KPIValue] = {}
                for task in sorted_tasks:
                    result = await self.compute_derived_metric(task.id)
                    if result:
                        results[task.id] = result

                return results

        except Exception as e:
            self.logger.error(f"Error computing derived metrics: {e}")
            return {}

    def get_derived_metric_definition(
        self, metric_id: str
    ) -> Optional[DerivedKPIDefinition]:
        """Get derived metric definition."""
        return self._derived_metrics.get(metric_id)

    def list_derived_metrics(self) -> List[str]:
        """List all derived metric IDs."""
        return list(self._derived_metrics.keys())

    def clear_cache(self, metric_id: Optional[str] = None) -> None:
        """Clear computation cache."""
        if metric_id:
            self._cache.pop(metric_id, None)
        else:
            self._cache.clear()
