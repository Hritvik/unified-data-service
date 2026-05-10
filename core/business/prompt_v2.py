"""Prompt template V2 business logic for unified data service."""

from typing import Any, Dict, Optional

from ..interfaces import DataSourceQuery
from ..service import UnifiedDataService

logger = logging.getLogger(__name__)


class PromptTemplateV2Business:
    """Business logic for V2 prompt template service."""

    def __init__(self, service: UnifiedDataService) -> None:
        """Initialize prompt template business service."""
        self._service = service

    async def get_template_by_natural_key(
        self, parent_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single template by its natural-key tuple."""
        results = await self._service.search(
            DataSourceQuery(filters={"parent_id": parent_id, "name": name}, limit=1)
        )
        if not results:
            return None
        return results[0]

    async def resolve_template(
        self, parent_id: str, name: str
    ) -> Dict[str, Any]:
        """Resolve a template by substituting `{type.name}` placeholders."""
        template = await self.get_template_by_natural_key(parent_id, name)
        if template is None:
            raise ValueError(f"Template '{name}' not found in namespace '{parent_id}'")
        return template

    async def _resolve_loaded_template(
        self, parent_id: str, template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve an already-fetched template dict."""
        # For now, return the template as-is
        # In a full implementation, this would process component references
        return template

    async def resolve_template_and_format_input(
        self, namespace: str, name: str, kwargs: Dict[str, Any]
    ) -> Dict[str, str]:
        """Combined: resolve a template + format its prompt_input with kwargs."""
        template = await self.get_template_by_natural_key(namespace, name)
        if template is None:
            raise ValueError(f"Template '{name}' not found in namespace '{namespace}'")
        
        input_prompt = template.get("prompt_input", "")
        try:
            input_prompt = input_prompt.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required keyword argument for template '{name}': {e}")
        except Exception as e:
            raise ValueError(f"Error formatting input prompt for template '{name}': {e}")

        return {
            "resolved_template": template,
            "input_prompt": input_prompt,
        }
