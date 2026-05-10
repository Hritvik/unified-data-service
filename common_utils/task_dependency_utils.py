"""
Task dependency sorting utilities.

This module provides utilities for sorting tasks based on their dependencies
using topological sorting algorithms.
"""

from typing import Dict, List, Protocol, Set, TypeVar, Generic
from dataclasses import dataclass


class TaskWithDependencies(Protocol):
    """Protocol for objects that have dependencies."""

    @property
    def id(self) -> str:
        """Unique identifier for the task."""
        ...

    @property
    def dependencies(self) -> List[str]:
        """List of task IDs that this task depends on."""
        ...


T = TypeVar("T", bound=TaskWithDependencies)


@dataclass
class TaskDependencyError(Exception):
    """Exception raised when task dependency issues are detected."""

    message: str
    cycle_path: List[str] = None
    missing_dependencies: List[str] = None


class TopologicalSorter(Generic[T]):
    """
    Generic topological sorter for tasks with dependencies.

    Uses Depth-First Search (DFS) based topological sorting algorithm
    to resolve task dependencies and detect circular dependencies.
    """

    def __init__(self, tasks: List[T]) -> None:
        """
        Initialize the sorter with a list of tasks.

        Args:
            tasks: List of tasks that implement TaskWithDependencies protocol
        """
        self.tasks = tasks
        self._task_map: Dict[str, T] = {task.id: task for task in tasks}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build the dependency graph from tasks."""
        for task in self.tasks:
            self._dependency_graph[task.id] = set(task.dependencies)

    def sort(self) -> List[T]:
        """
        Sort tasks in dependency order using topological sort.

        Returns:
            List of tasks sorted such that dependencies come before dependents

        Raises:
            TaskDependencyError: If circular dependencies are detected or
                                dependencies are missing
        """
        # Check for missing dependencies first
        self._validate_dependencies()

        sorted_tasks: List[T] = []
        visited: Set[str] = set()
        visiting: Set[str] = set()  # For cycle detection

        def visit(task_id: str, path: List[str]) -> None:
            """
            Visit a task and its dependencies using DFS.

            Args:
                task_id: ID of the task to visit
                path: Current path for cycle detection
            """
            if task_id in visiting:
                # Circular dependency detected
                cycle_start = path.index(task_id)
                cycle = path[cycle_start:] + [task_id]
                raise TaskDependencyError(
                    f"Circular dependency detected: {' -> '.join(cycle)}",
                    cycle_path=cycle,
                )

            if task_id in visited:
                return

            # Mark as currently being visited
            visiting.add(task_id)

            # Visit all dependencies first
            for dep_id in self._dependency_graph.get(task_id, []):
                if dep_id in self._task_map:  # Only visit existing dependencies
                    visit(dep_id, path + [task_id])

            # Mark as completely visited
            visiting.remove(task_id)
            visited.add(task_id)

            # Add to sorted list
            if task_id in self._task_map:
                sorted_tasks.append(self._task_map[task_id])

        # Visit all tasks
        for task_id in self._dependency_graph:
            if task_id not in visited:
                visit(task_id, [])

        return sorted_tasks

    def _validate_dependencies(self) -> None:
        """
        Validate that all dependencies exist.

        Raises:
            TaskDependencyError: If any dependencies are missing
        """
        missing_deps: List[str] = []

        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in self._task_map:
                    missing_deps.append(f"{task.id} -> {dep_id}")

        if missing_deps:
            raise TaskDependencyError(
                f"Missing dependencies found: {', '.join(missing_deps)}",
                missing_dependencies=missing_deps,
            )

    def get_dependency_levels(self) -> Dict[str, int]:
        """
        Get the dependency level for each task.

        Level 0 tasks have no dependencies, level 1 tasks depend only on
        level 0 tasks, etc.

        Returns:
            Dictionary mapping task IDs to their dependency levels
        """
        sorted_tasks = self.sort()
        levels: Dict[str, int] = {}

        for task in sorted_tasks:
            if not task.dependencies:
                levels[task.id] = 0
            else:
                max_dep_level = max(
                    levels.get(dep_id, 0)
                    for dep_id in task.dependencies
                    if dep_id in levels
                )
                levels[task.id] = max_dep_level + 1

        return levels


class KahnTopologicalSorter(Generic[T]):
    """
    Alternative implementation using Kahn's algorithm (BFS-based).

    This implementation is useful when you want to process tasks level by level
    or need to handle tasks in batches where tasks at the same level can be
    executed in parallel.
    """

    def __init__(self, tasks: List[T]) -> None:
        """
        Initialize the sorter with a list of tasks.

        Args:
            tasks: List of tasks that implement TaskWithDependencies protocol
        """
        self.tasks = tasks
        self._task_map: Dict[str, T] = {task.id: task for task in tasks}
        self._in_degree: Dict[str, int] = {}
        self._adjacency_list: Dict[str, List[str]] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the graph and calculate in-degrees."""
        # Initialize in-degree and adjacency list
        for task in self.tasks:
            self._in_degree[task.id] = 0
            self._adjacency_list[task.id] = []

        # Build adjacency list and calculate in-degrees
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id in self._task_map:
                    self._adjacency_list[dep_id].append(task.id)
                    self._in_degree[task.id] += 1

    def sort(self) -> List[T]:
        """
        Sort tasks using Kahn's algorithm.

        Returns:
            List of tasks sorted in dependency order

        Raises:
            TaskDependencyError: If circular dependencies are detected
        """
        # Check for missing dependencies
        self._validate_dependencies()

        # Find all tasks with no dependencies
        queue: List[str] = [
            task_id for task_id, degree in self._in_degree.items() if degree == 0
        ]

        sorted_tasks: List[T] = []

        while queue:
            # Remove a task with no dependencies
            current_id = queue.pop(0)
            sorted_tasks.append(self._task_map[current_id])

            # For each task that depends on the current task
            for dependent_id in self._adjacency_list[current_id]:
                # Reduce its in-degree
                self._in_degree[dependent_id] -= 1

                # If it has no more dependencies, add to queue
                if self._in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for cycles
        if len(sorted_tasks) != len(self.tasks):
            remaining_tasks = [
                task_id for task_id, degree in self._in_degree.items() if degree > 0
            ]
            raise TaskDependencyError(
                f"Circular dependency detected among tasks: {remaining_tasks}"
            )

        return sorted_tasks

    def _validate_dependencies(self) -> None:
        """
        Validate that all dependencies exist.

        Raises:
            TaskDependencyError: If any dependencies are missing
        """
        missing_deps: List[str] = []

        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in self._task_map:
                    missing_deps.append(f"{task.id} -> {dep_id}")

        if missing_deps:
            raise TaskDependencyError(
                f"Missing dependencies found: {', '.join(missing_deps)}",
                missing_dependencies=missing_deps,
            )

    def get_parallel_batches(self) -> List[List[T]]:
        """
        Get tasks grouped into batches that can be executed in parallel.

        Returns:
            List of batches, where each batch contains tasks that can run in parallel
        """
        # Work with a copy of in-degrees
        in_degree = self._in_degree.copy()
        batches: List[List[T]] = []

        while any(degree >= 0 for degree in in_degree.values()):
            # Find all tasks with no dependencies in this iteration
            current_batch_ids = [
                task_id for task_id, degree in in_degree.items() if degree == 0
            ]

            if not current_batch_ids:
                # No tasks with zero dependencies - circular dependency
                remaining = [tid for tid, deg in in_degree.items() if deg >= 0]
                raise TaskDependencyError(
                    f"Circular dependency detected among tasks: {remaining}"
                )

            # Add current batch
            current_batch = [self._task_map[tid] for tid in current_batch_ids]
            batches.append(current_batch)

            # Remove these tasks and update in-degrees
            for task_id in current_batch_ids:
                in_degree[task_id] = -1  # Mark as processed

                # Reduce in-degree for dependent tasks
                for dependent_id in self._adjacency_list[task_id]:
                    if in_degree[dependent_id] >= 0:
                        in_degree[dependent_id] -= 1

        return batches


# Convenience functions
def sort_tasks_by_dependencies(tasks: List[T], algorithm: str = "dfs") -> List[T]:
    """
    Sort tasks by their dependencies using the specified algorithm.

    Args:
        tasks: List of tasks implementing TaskWithDependencies protocol
        algorithm: Algorithm to use ("dfs" for DFS-based, "kahn" for Kahn's algorithm)

    Returns:
        List of tasks sorted in dependency order

    Raises:
        TaskDependencyError: If dependency issues are detected
        ValueError: If invalid algorithm is specified
    """
    if algorithm == "dfs":
        sorter = TopologicalSorter(tasks)
        return sorter.sort()
    elif algorithm == "kahn":
        sorter = KahnTopologicalSorter(tasks)
        return sorter.sort()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}. Use 'dfs' or 'kahn'")


def get_task_dependency_levels(tasks: List[T]) -> Dict[str, int]:
    """
    Get dependency levels for tasks.

    Args:
        tasks: List of tasks implementing TaskWithDependencies protocol

    Returns:
        Dictionary mapping task IDs to their dependency levels
    """
    sorter = TopologicalSorter(tasks)
    return sorter.get_dependency_levels()


def get_parallel_execution_batches(tasks: List[T]) -> List[List[T]]:
    """
    Group tasks into batches that can be executed in parallel.

    Args:
        tasks: List of tasks implementing TaskWithDependencies protocol

    Returns:
        List of batches where tasks in each batch can run in parallel
    """
    sorter = KahnTopologicalSorter(tasks)
    return sorter.get_parallel_batches()
