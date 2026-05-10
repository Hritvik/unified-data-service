"""
Common utilities and shared functionality for the modelswitch project.

This package contains reusable components including:
- Repository patterns
- Metrics and monitoring
- Logging utilities
- Enums and constants
- Cache mixins and strategies
- Utility functions
- Singleton mixin
"""

# Logger utilities
# Constants (import the module to access constants)
# Metrics (import the module to access metrics)
# Subpackages
from . import constants, metrics, models

# Cache mixin (in common_utils.cache)
from .cache import CacheMixin

# Enums
from .enums import (
    APIContract,
    CircuitBreakerState,
    CircuitBreakerStrategy,
    Modality,
    ModelCapability,
    ModelProvider,
    RetryStrategyType,
)

# File operations
# from .file_operations import FileOperationsService

# JSON utilities
from .json_utils import clean_json_response, replace_empty_dicts_with_none

# Logger functions
from .logger import (
    get_logger,
    get_loguru_logger,
    get_standard_logger,
    setup_loguru,
    setup_standard_logging,
)

# Repository pattern
from .repository import (
    IMongoDocumentRepository,
    MongoDocumentRepository,
    RepositoryFactory,
)

# String utilities
from .str_utils import replace_placeholders

# Task dependency utilities
from .task_dependency_utils import (
    KahnTopologicalSorter,
    TaskDependencyError,
    TaskWithDependencies,
    TopologicalSorter,
    get_parallel_execution_batches,
    get_task_dependency_levels,
    sort_tasks_by_dependencies,
)

__all__ = [
    # Logger functions
    "setup_loguru",
    "get_loguru_logger",
    "get_standard_logger",
    "setup_standard_logging",
    "get_logger",
    # Enums
    "APIContract",
    "Modality",
    "ModelCapability",
    "ModelProvider",
    "CircuitBreakerState",
    "CircuitBreakerStrategy",
    "RetryStrategyType",
    # Repository classes
    "IMongoDocumentRepository",
    "MongoDocumentRepository",
    "RepositoryFactory",
    # Cache mixin
    "CacheMixin",
    # File operations
    # "FileOperationsService",
    # Modules
    "constants",
    "metrics",
    "models",
    # JSON utilities
    "clean_json_response",
    "replace_empty_dicts_with_none",
    # String utilities
    "replace_placeholders",
    # Task dependency utilities
    "TaskDependencyError",
    "TaskWithDependencies",
    "TopologicalSorter",
    "KahnTopologicalSorter",
    "sort_tasks_by_dependencies",
    "get_task_dependency_levels",
    "get_parallel_execution_batches",
]
