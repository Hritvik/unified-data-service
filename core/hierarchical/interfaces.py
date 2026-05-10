"""Hierarchical unified data service interfaces.

This module defines interfaces for tree-aware data operations
and hierarchical service management.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel

from ..interfaces import IDataSource, IUnifiedService, DataSourceQuery, PaginatedResult

T = TypeVar("T")  # Entity type
K = TypeVar("K")  # Key type


class HierarchyConfig(BaseModel):
    """Configuration for hierarchical data structure."""
    
    name: str
    description: Optional[str] = None
    root_node_type: str
    node_type_field: str = "type"
    parent_id_field: str = "parent_id"
    children_field: str = "children"
    path_field: Optional[str] = None
    max_depth: int = 10
    enable_orphan_cleanup: bool = True
    cascade_delete: bool = False


class NodeConfig(BaseModel):
    """Configuration for a node in hierarchical structure."""
    
    name: str
    description: Optional[str] = None
    node_type: str
    metadata: Dict[str, Any] = {}
    required_fields: List[str] = []
    allowed_child_types: List[str] = []


class HierarchicalQuery(DataSourceQuery):
    """Extended query with hierarchical parameters."""
    
    include_descendants: bool = False
    include_ancestors: bool = False
    max_depth: Optional[int] = None
    start_node_id: Optional[str] = None
    ancestor_types: Optional[List[str]] = None


class HierarchicalOperationResult(BaseModel):
    """Result of hierarchical operation."""
    
    success: bool = True
    affected_nodes: List[str] = []
    orphaned_nodes: List[str] = []
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class IHierarchicalUnifiedService(IUnifiedService[T, K], ABC):
    """Interface for hierarchical unified data service."""
    
    @abstractmethod
    async def get_descendants(
        self,
        node_id: K,
        query: Optional[HierarchicalQuery] = None
    ) -> List[T]:
        """Get all descendants of a node."""
        ...
    
    @abstractmethod
    async def get_ancestors(
        self,
        node_id: K,
        query: Optional[HierarchicalQuery] = None
    ) -> List[T]:
        """Get all ancestors of a node."""
        ...
    
    @abstractmethod
    async def get_tree(
        self,
        root_id: Optional[K] = None,
        query: Optional[HierarchicalQuery] = None
    ) -> Dict[str, Any]:
        """Get complete tree structure."""
        ...
    
    @abstractmethod
    async def add_child(
        self,
        parent_id: K,
        child_data: Dict[str, Any]
        child_type: str
    ) -> HierarchicalOperationResult:
        """Add a child node to a parent."""
        ...
    
    @abstractmethod
    async def remove_child(
        self,
        parent_id: K,
        child_id: K,
        force_orphan_cleanup: bool = False
    ) -> HierarchicalOperationResult:
        """Remove a child node from a parent."""
        ...
    
    @abstractmethod
    async def move_node(
        self,
        node_id: K,
        new_parent_id: Optional[K] = None,
        force_orphan_cleanup: bool = False
    ) -> HierarchicalOperationResult:
        """Move a node to a new parent."""
        ...
    
    @abstractmethod
    async def delete_node(
        self,
        node_id: K,
        force_orphan_cleanup: bool = False
    ) -> HierarchicalOperationResult:
        """Delete a node and handle orphan cleanup."""
        ...
    
    @abstractmethod
    async def get_orphaned_nodes(
        self,
        query: Optional[HierarchicalQuery] = None
    ) -> List[T]:
        """Get all orphaned nodes."""
        ...
    
    @abstractmethod
    async def cleanup_orphans(
        self,
        query: Optional[HierarchicalQuery] = None
    ) -> Dict[str, Any]:
        """Clean up orphaned nodes."""
        ...
    
    @abstractmethod
    async def export_hierarchy(
        self,
        root_id: Optional[K] = None,
        query: Optional[HierarchicalQuery] = None
    ) -> Dict[str, Any]:
        """Export hierarchy with all relationships preserved."""
        ...
