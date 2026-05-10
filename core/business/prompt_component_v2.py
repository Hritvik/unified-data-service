"""Prompt component V2 business logic for unified data service."""

from typing import Any, Dict, Optional

from ..interfaces import DataSourceQuery
from ..service import UnifiedDataService

logger = logging.getLogger(__name__)


class PromptComponentV2Business:
    """Business logic for V2 prompt component service."""

    def __init__(self, service: UnifiedDataService) -> None:
        """Initialize prompt component business service."""
        self._service = service
        self._component_type = "prompt-component-v2"

    async def get_component_by_natural_key(
        self, parent_id: str, component_type: str, component_name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single component by its compound natural-key."""
        results = await self._service.search(
            DataSourceQuery(filters={"parent_id": parent_id, "component_type": component_type, "component_name": component_name}, limit=1)
        )
        if not results:
            return None
        return results[0]

    async def create_component(
        self, parent_id: str, component_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new component."""
        component_data["component_type"] = component_data.get("type", "default")
        component_data["component_name"] = component_data.get("name", "unnamed")
        component_data["content"] = component_data.get("content", "")
        
        result = await self._service.create(component_data)
        
        return {
            "component_id": result.get("id"),
            "parent_id": parent_id,
            "component_type": component_data["component_type"],
            "component_name": component_data["component_name"],
            "content": component_data["content"]
        }

    async def update_component(
        self, component_id: str, component_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing component."""
        result = await self._service.update(component_id, component_data)
        
        return {
            "component_id": result.get("id"),
            "parent_id": result.get("parent_id"),
            "component_type": result.get("component_type"),
            "component_name": result.get("component_name"),
            "content": result.get("content")
        }

    async def delete_component(self, component_id: str) -> bool:
        """Delete a component."""
        result = await self._service.delete(component_id)
        return result

    async def list_components(
        self, parent_id: Optional[str] = None, component_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List components by parent and type."""
        filters = {}
        if parent_id:
            filters["parent_id"] = parent_id
        if component_type:
            filters["component_type"] = component_type
        
        results = await self._service.search(DataSourceQuery(filters=filters))
        
        return {
            "components": results,
            "parent_id": parent_id,
            "component_type": component_type
        }
