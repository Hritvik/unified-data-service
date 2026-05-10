"""Hierarchical (parent-child tree) unified data service.

Composes N existing UnifiedDataService instances into an N-level tree,
adding tree-aware operations (cascade delete, get-with-descendants,
replace-children, move) without touching per-level CRUD/cache/metrics.

M:N cross-references are configured separately on ServiceConfig.references
and resolved at read time; they are not part of the ownership tree.
"""

from .factory import HierarchicalServiceFactory
from .service import CascadeResult, HierarchicalUnifiedService, TreeNode

__all__ = [
    "CascadeResult",
    "HierarchicalServiceFactory",
    "HierarchicalUnifiedService",
    "TreeNode",
]
