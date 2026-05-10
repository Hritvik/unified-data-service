"""
Task models for dependency sorting and task management.

This module provides concrete implementations of tasks that can be used
with the task dependency sorting utilities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Priority levels for tasks."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """
    Basic task implementation with dependency support.

    This class implements the TaskWithDependencies protocol and can be used
    with the task dependency sorting utilities.
    """

    id: str
    name: str
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate task after initialization."""
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.name:
            raise ValueError("Task name cannot be empty")

    def add_dependency(self, task_id: str) -> None:
        """Add a dependency to this task."""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)

    def remove_dependency(self, task_id: str) -> None:
        """Remove a dependency from this task."""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)

    def has_dependency(self, task_id: str) -> bool:
        """Check if this task depends on another task."""
        return task_id in self.dependencies

    def is_ready(self, completed_tasks: List[str]) -> bool:
        """Check if all dependencies are completed."""
        return all(dep_id in completed_tasks for dep_id in self.dependencies)


@dataclass
class ExecutableTask(Task):
    """
    Task with execution capabilities.

    Extends the basic Task with execution function and result storage.
    """

    execution_function: Optional[callable] = None
    result: Any = None
    error: Optional[Exception] = None
    execution_time_seconds: Optional[float] = None

    async def execute(self) -> Any:
        """
        Execute the task if an execution function is provided.

        Returns:
            Result of the execution function

        Raises:
            ValueError: If no execution function is set
            Exception: Any exception raised by the execution function
        """
        if not self.execution_function:
            raise ValueError(f"No execution function set for task {self.id}")

        try:
            self.status = TaskStatus.IN_PROGRESS
            if hasattr(self.execution_function, "__call__"):
                # Handle both sync and async functions
                import inspect

                if inspect.iscoroutinefunction(self.execution_function):
                    result = await self.execution_function()
                else:
                    result = self.execution_function()

                self.result = result
                self.status = TaskStatus.COMPLETED
                return result
        except Exception as e:
            self.error = e
            self.status = TaskStatus.FAILED
            raise


@dataclass
class WorkflowTask(Task):
    """
    Task that represents a workflow step with additional workflow metadata.
    """

    workflow_id: str = ""
    step_number: int = 0
    parallel_group: Optional[str] = None
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3

    def can_run_in_parallel_with(self, other: "WorkflowTask") -> bool:
        """Check if this task can run in parallel with another task."""
        return (
            self.parallel_group is not None
            and other.parallel_group is not None
            and self.parallel_group == other.parallel_group
        )


# Factory functions for creating common task patterns


def create_simple_task(
    task_id: str, name: str, dependencies: Optional[List[str]] = None
) -> Task:
    """
    Create a simple task with minimal configuration.

    Args:
        task_id: Unique identifier for the task
        name: Human-readable name for the task
        dependencies: List of task IDs this task depends on

    Returns:
        Configured Task instance
    """
    return Task(id=task_id, name=name, dependencies=dependencies or [])


def create_executable_task(
    task_id: str,
    name: str,
    execution_function: callable,
    dependencies: Optional[List[str]] = None,
) -> ExecutableTask:
    """
    Create an executable task with a function to run.

    Args:
        task_id: Unique identifier for the task
        name: Human-readable name for the task
        execution_function: Function to execute when the task runs
        dependencies: List of task IDs this task depends on

    Returns:
        Configured ExecutableTask instance
    """
    return ExecutableTask(
        id=task_id,
        name=name,
        execution_function=execution_function,
        dependencies=dependencies or [],
    )


def create_workflow_step(
    task_id: str,
    name: str,
    workflow_id: str,
    step_number: int,
    dependencies: Optional[List[str]] = None,
    parallel_group: Optional[str] = None,
) -> WorkflowTask:
    """
    Create a workflow task representing a step in a larger workflow.

    Args:
        task_id: Unique identifier for the task
        name: Human-readable name for the task
        workflow_id: ID of the workflow this task belongs to
        step_number: Order of this step in the workflow
        dependencies: List of task IDs this task depends on
        parallel_group: Group name for parallel execution

    Returns:
        Configured WorkflowTask instance
    """
    return WorkflowTask(
        id=task_id,
        name=name,
        workflow_id=workflow_id,
        step_number=step_number,
        dependencies=dependencies or [],
        parallel_group=parallel_group,
    )
