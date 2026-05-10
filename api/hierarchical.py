"""Hierarchical REST endpoints for unified data service.

This module provides REST endpoints for tree-aware operations
exposed by HierarchicalUnifiedService instances.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query, Path

from api.main import service_registry
from common_utils.unified_data.hierarchical.service import HierarchicalUnifiedService


router = APIRouter(prefix="/api/v1/hierarchical")


def get_hierarchical_service(service_name: str) -> HierarchicalUnifiedService:
    """Get hierarchical service instance by name."""
    service = service_registry.get(service_name)
    if service is None or not isinstance(service, HierarchicalUnifiedService):
        raise HTTPException(status_code=404, detail=f"Hierarchical service '{service_name}' not found")
    return service


@router.post("/{service_name}/{kind}", response_model=Dict[str, Any])
async def create_with_children(
    service_name: str = Path(...),
    kind: str = Path(...),
    payload: Dict[str, Any] = Body(...)
):
    """Create a parent entity and recursively create its children."""
    service = get_hierarchical_service(service_name)
    
    # Payload should have 'entity' and optionally 'children'
    entity_data = payload.get("entity", payload) # Support both flat and nested
    children = payload.get("children")
    
    try:
        tree = await service.create_with_children(
            kind=kind,
            data=entity_data,
            children=children
        )
        # Serialization handled by FastAPI's jsonable_encoder via TreeNode.model_dump
        return tree.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{service_name}/{kind}/{node_id}", response_model=Dict[str, Any])
async def get_with_descendants(
    service_name: str = Path(...),
    kind: str = Path(...),
    node_id: str = Path(...),
    depth: int = Query(-1, description="Depth of descendants to fetch (-1 for full tree)"),
):
    """Fetch an entity and its descendants up to depth."""
    service = get_hierarchical_service(service_name)
    
    tree = await service.get_with_descendants(kind=kind, id=node_id, depth=depth)
    if tree is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' of kind '{kind}' not found")
    
    return tree.model_dump()


@router.delete("/{service_name}/{kind}/{node_id}", response_model=Dict[str, Any])
async def delete_cascade(
    service_name: str = Path(...),
    kind: str = Path(...),
    node_id: str = Path(...),
    force_orphan_cleanup: bool = Query(False, description="Force cleanup of orphaned nodes"),
    children_only: bool = Query(False, description="Delete children only, keep the parent"),
):
    """Depth-first cascade delete."""
    service = get_hierarchical_service(service_name)
    result = await service.delete_cascade(
        kind=kind,
        id=node_id,
        force_orphan_cleanup=force_orphan_cleanup,
        children_only=children_only
    )
    
    return result.model_dump()
