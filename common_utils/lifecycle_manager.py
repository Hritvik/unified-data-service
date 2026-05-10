"""
Centralized lifecycle management for all application modules.

This module provides a unified interface for managing startup and shutdown
of all application modules, including DI containers, services, and resources.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from .logger import get_logger
from .task_dependency_utils import (
    TaskDependencyError,
    get_parallel_execution_batches,
    sort_tasks_by_dependencies,
)

logger = get_logger(__name__)


class LifecyclePhase(Enum):
    """Lifecycle phases for module initialization."""

    INFRASTRUCTURE = "infrastructure"  # Layer 0: MongoDB, Redis, GCS
    REGISTRIES = "registries"  # Layer 1: Data registries
    CORE_CLIENTS = "core_clients"  # Layer 2: REST client, Model Bridge
    BUSINESS_SERVICES = "business_services"  # Layer 3: App, Ticket Resolution
    OBSERVABILITY = "observability"  # Layer 4: Cache registry, monitoring
    FINALIZATION = "finalization"  # Layer 5: Final cleanup


class LifecycleManager(Protocol):
    """Protocol for module lifecycle managers."""

    async def startup(self) -> None:
        """Initialize the module."""
        ...

    async def shutdown(self) -> None:
        """Shutdown the module."""
        ...


@dataclass
class ModuleLifecycle:
    """Configuration for a module's lifecycle."""

    name: str
    startup_func: Callable[[], Any]
    shutdown_func: Callable[[], Any]
    phase: LifecyclePhase
    required: bool = True
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    @property
    def id(self) -> str:
        """Return the module name as the unique identifier."""
        return self.name


class ApplicationLifecycleManager:
    """
    Centralized lifecycle manager for the entire application.

    Manages startup and shutdown of all modules in the correct order,
    with proper error handling and dependency resolution.
    """

    def __init__(self):
        self.modules: Dict[str, ModuleLifecycle] = {}
        self._startup_completed: bool = False
        self._shutdown_completed: bool = False

    def register_module(
        self,
        name: str,
        startup_func: Callable[[], Any],
        shutdown_func: Callable[[], Any],
        phase: LifecyclePhase,
        required: bool = True,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """
        Register a module for lifecycle management.

        Args:
            name: Module name
            startup_func: Function to call during startup
            shutdown_func: Function to call during shutdown
            phase: Lifecycle phase for this module
            required: Whether failure should stop the application
            dependencies: List of module names this module depends on
        """
        dependencies = dependencies or []

        # Validate dependencies
        self._validate_dependencies(name, phase, dependencies)

        self.modules[name] = ModuleLifecycle(
            name=name,
            startup_func=startup_func,
            shutdown_func=shutdown_func,
            phase=phase,
            required=required,
            dependencies=dependencies,
        )
        logger.debug(f"Registered module '{name}' for lifecycle management")

    def _validate_dependencies(
        self, module_name: str, phase: LifecyclePhase, dependencies: List[str]
    ) -> None:
        """Validate module dependencies and warn about potential issues."""
        if not dependencies:
            return

        # Get all existing modules by phase
        phase_modules = {}
        for phase_enum in LifecyclePhase:
            phase_modules[phase_enum] = [
                m.name for m in self.modules.values() if m.phase == phase_enum
            ]

        # Check for same-phase dependencies (potential circular dependency)
        same_phase_deps = [
            dep for dep in dependencies if dep in phase_modules.get(phase, [])
        ]
        if same_phase_deps:
            logger.warning(
                f"Module '{module_name}' in phase '{phase.value}' depends on same-phase modules: {same_phase_deps}. "
                f"This may cause circular dependency issues. Consider moving dependencies to earlier phases."
            )

        # Check for dependencies on later phases (invalid)
        phase_order = list(LifecyclePhase)
        current_phase_index = phase_order.index(phase)

        for dep in dependencies:
            for dep_phase, dep_modules in phase_modules.items():
                if dep in dep_modules:
                    dep_phase_index = phase_order.index(dep_phase)
                    if dep_phase_index > current_phase_index:
                        logger.error(
                            f"Module '{module_name}' in phase '{phase.value}' depends on '{dep}' "
                            f"which is in later phase '{dep_phase.value}'. This is invalid."
                        )
                    break

    def _get_modules_by_phase(self, phase: LifecyclePhase) -> List[ModuleLifecycle]:
        """Get all modules for a specific phase."""
        return [module for module in self.modules.values() if module.phase == phase]

    def _check_dependencies(
        self, module: ModuleLifecycle, completed_modules: set
    ) -> bool:
        """Check if all dependencies for a module are satisfied."""
        return all(dep in completed_modules for dep in module.dependencies)

    def _sort_modules_by_dependencies(
        self, modules: List[ModuleLifecycle], completed_modules: set = None
    ) -> List[ModuleLifecycle]:
        """
        Sort modules by their dependencies to ensure proper initialization order.

        Uses the centralized task dependency sorting utility with improved error handling.
        """
        if completed_modules is None:
            completed_modules = set()

        try:
            # Create filtered modules for sorting - only include same-phase dependencies
            filtered_modules = []
            for module in modules:
                # Only include dependencies that are in the same phase (not yet completed)
                # Cross-phase dependencies are already satisfied by completed_modules
                same_phase_deps = [
                    dep for dep in module.dependencies if dep not in completed_modules
                ]

                # Create a temporary module with filtered dependencies for sorting
                from dataclasses import dataclass
                from typing import List as TypingList

                @dataclass
                class FilteredModule:
                    id: str
                    name: str
                    dependencies: TypingList[str]
                    phase: str
                    required: bool
                    startup_func: callable
                    shutdown_func: callable

                filtered_module = FilteredModule(
                    id=module.name,  # Use name as id
                    name=module.name,
                    dependencies=same_phase_deps,  # Only same-phase deps for sorting
                    phase=module.phase.value,
                    required=module.required,
                    startup_func=module.startup_func,
                    shutdown_func=module.shutdown_func,
                )
                filtered_modules.append(filtered_module)

            # Use our new task dependency sorting utility with filtered dependencies
            sorted_filtered = sort_tasks_by_dependencies(
                filtered_modules, algorithm="dfs"
            )

            # Map back to original modules in the same order
            name_to_module = {module.name: module for module in modules}
            return [name_to_module[filtered.name] for filtered in sorted_filtered]
        except TaskDependencyError as e:
            # Convert to a more specific lifecycle error
            phase_names = [module.phase.value for module in modules]
            error_msg = f"Dependency error in lifecycle phase(s) {set(phase_names)}: {e.message}"

            if e.cycle_path:
                error_msg += f" Cycle detected: {' -> '.join(e.cycle_path)}"
            if e.missing_dependencies:
                error_msg += (
                    f" Missing dependencies: {', '.join(e.missing_dependencies)}"
                )

            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_parallel_startup_batches(
        self, phase: LifecyclePhase
    ) -> List[List[ModuleLifecycle]]:
        """
        Get modules in batches that can be started in parallel within a phase.

        Args:
            phase: The lifecycle phase to get parallel batches for

        Returns:
            List of batches where modules in each batch can run in parallel
        """
        phase_modules = self._get_modules_by_phase(phase)
        if not phase_modules:
            return []

        try:
            return get_parallel_execution_batches(phase_modules)
        except TaskDependencyError as e:
            error_msg = f"Dependency error in phase {phase.value}: {e.message}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def startup(self) -> None:
        """
        Start up all modules in the correct order.

        Modules are started in phases, with dependencies resolved within each phase.
        """
        if self._startup_completed:
            logger.warning("Startup already completed, skipping")
            return

        logger.info("Starting application lifecycle...")

        completed_modules = set()
        failed_modules = []

        # Process modules by phase
        for phase in LifecyclePhase:
            phase_modules = self._get_modules_by_phase(phase)
            if not phase_modules:
                continue

            logger.info(f"Starting phase: {phase.value}")

            # Sort modules by dependencies within this phase
            # Pass completed modules so cross-phase dependencies can be resolved
            sorted_phase_modules = self._sort_modules_by_dependencies(
                phase_modules, completed_modules
            )

            # Start modules in this phase
            for module in sorted_phase_modules:
                if not self._check_dependencies(module, completed_modules):
                    # Get all modules from previous phases for better error reporting
                    previous_phase_modules = set()
                    for prev_phase in LifecyclePhase:
                        if prev_phase == phase:
                            break
                        prev_modules = self._get_modules_by_phase(prev_phase)
                        previous_phase_modules.update(mod.name for mod in prev_modules)

                    missing_deps = [
                        dep
                        for dep in module.dependencies
                        if dep not in completed_modules
                    ]
                    error_msg = f"Module '{module.name}' dependencies not met: {missing_deps}. Available modules: {sorted(completed_modules)}. Previous phase modules: {sorted(previous_phase_modules)}"
                    if module.required:
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                    else:
                        logger.warning(f"{error_msg}, skipping module")
                        continue

                try:
                    logger.info(f"Starting module: {module.name}")

                    # Handle both sync and async functions
                    if asyncio.iscoroutinefunction(module.startup_func):
                        await module.startup_func()
                    else:
                        module.startup_func()

                    completed_modules.add(module.name)
                    logger.info(f"Module '{module.name}' started successfully")

                except Exception as e:
                    error_msg = f"Failed to start module '{module.name}': {e}"
                    if module.required:
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                    else:
                        logger.warning(f"{error_msg}, continuing with other modules")
                        failed_modules.append(module.name)

        self._startup_completed = True

        if failed_modules:
            logger.warning(
                f"Startup completed with {len(failed_modules)} failed modules: {failed_modules}"
            )
        else:
            logger.info("Application startup completed successfully")

    async def shutdown(self) -> None:
        """
        Shutdown all modules in reverse order.

        Modules are shut down in reverse phase order to ensure proper cleanup.
        """
        if self._shutdown_completed:
            logger.warning("Shutdown already completed, skipping")
            return

        logger.info("Shutting down application lifecycle...")

        failed_modules = []

        # Process modules in reverse phase order
        for phase in reversed(list(LifecyclePhase)):
            phase_modules = self._get_modules_by_phase(phase)
            if not phase_modules:
                continue

            logger.info(f"Shutting down phase: {phase.value}")

            # Shutdown modules in this phase
            for module in phase_modules:
                try:
                    logger.info(f"Shutting down module: {module.name}")

                    # Handle both sync and async functions
                    if asyncio.iscoroutinefunction(module.shutdown_func):
                        await module.shutdown_func()
                    else:
                        module.shutdown_func()

                    logger.info(f"Module '{module.name}' shut down successfully")

                except Exception as e:
                    error_msg = f"Failed to shutdown module '{module.name}': {e}"
                    logger.error(error_msg)
                    failed_modules.append(module.name)
                    # Continue with other modules during shutdown

        self._shutdown_completed = True

        if failed_modules:
            logger.warning(
                f"Shutdown completed with {len(failed_modules)} failed modules: {failed_modules}"
            )
        else:
            logger.info("Application shutdown completed successfully")


# Global lifecycle manager instance
lifecycle_manager = ApplicationLifecycleManager()


def register_module_lifecycle(
    name: str,
    startup_func: Callable[[], Any],
    shutdown_func: Callable[[], Any],
    phase: LifecyclePhase,
    required: bool = True,
    dependencies: Optional[List[str]] = None,
) -> None:
    """
    Convenience function to register a module with the global lifecycle manager.

    Args:
        name: Module name
        startup_func: Function to call during startup
        shutdown_func: Function to call during shutdown
        phase: Lifecycle phase for this module
        required: Whether failure should stop the application
        dependencies: List of module names this module depends on
    """
    lifecycle_manager.register_module(
        name=name,
        startup_func=startup_func,
        shutdown_func=shutdown_func,
        phase=phase,
        required=required,
        dependencies=dependencies,
    )


async def startup_application() -> None:
    """Start up the entire application."""
    await lifecycle_manager.startup()


async def shutdown_application() -> None:
    """Shutdown the entire application."""
    await lifecycle_manager.shutdown()


def get_lifecycle_manager() -> ApplicationLifecycleManager:
    """Get the global lifecycle manager instance."""
    return lifecycle_manager
