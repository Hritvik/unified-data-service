"""V2 business-logic classes for prompt_registry.

Wired through ``business_logic_class`` on the V2 ServiceConfig YAMLs;
ServiceFactory injects the per-entity ``UnifiedDataService`` into each
business class' constructor and binds the instance to ``service.business``.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, Optional, List

from core.interfaces import DataSourceQuery
from core.service import UnifiedDataService
from factories.service_factory import ServiceFactory

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def _entity_to_dict(entity: Any) -> Dict[str, Any]:
    """Serialize an entity to a JSON-friendly dict."""
    if isinstance(entity, dict):
        return entity
    if hasattr(entity, "model_dump"):
        try:
            return entity.model_dump(mode="json")
        except TypeError:
            return entity.model_dump()
    if hasattr(entity, "dict"):
        return entity.dict()
    return dict(vars(entity))


class PromptTemplateV2Business:
    """Business logic for the V2 prompt template service."""

    def __init__(self, service: UnifiedDataService) -> None:
        self._service = service
        self._component_service_name = "prompt-component" # Name in registry

    async def get_template_by_natural_key(
        self, parent_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single template by its natural-key tuple."""
        results = await self._service.search(
            DataSourceQuery(filters={"parent_id": parent_id, "name": name}, limit=1)
        )
        if not results:
            return None
        return _entity_to_dict(results[0])

    async def resolve_template(
        self, parent_id: str, name: str
    ) -> Dict[str, Any]:
        """Resolve a template by substituting `{type.name}` placeholders."""
        template = await self.get_template_by_natural_key(parent_id, name)
        if template is None:
            raise ValueError(
                f"Template '{name}' not found in namespace '{parent_id}'"
            )
        return await self._resolve_loaded_template(parent_id, template)

    async def _resolve_loaded_template(
        self, parent_id: str, template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve an already-fetched template dict."""
        component_service = ServiceFactory.get_service(self._component_service_name)
        if component_service is None:
            raise ValueError(
                f"Component service '{self._component_service_name}' is not registered"
            )

        original = template.get("template", "")
        resolved = original
        resolved_components: Dict[str, Dict[str, Any]] = {}
        unresolved: List[str] = []

        for ref in template.get("components", []) or []:
            if not isinstance(ref, str) or "." not in ref:
                unresolved.append(f"{ref} (malformed; expected 'type.name')")
                continue
            ctype, cname = ref.split(".", 1)
            results = await component_service.search(
                DataSourceQuery(
                    filters={
                        "parent_id": parent_id,
                        "component_type": ctype,
                        "component_name": cname,
                    },
                    limit=1,
                )
            )
            if not results:
                unresolved.append(ref)
                continue
            component = _entity_to_dict(results[0])
            resolved_components[ref] = {
                "content": component.get("content"),
                "component_name": component.get("component_name"),
                "component_type": component.get("component_type"),
            }
            resolved = resolved.replace(f"{{{ref}}}", component.get("content", ""))

        if unresolved:
            raise ValueError(
                f"Could not resolve the following components: {unresolved}"
            )

        return {
            "template_name": template.get("name"),
            "template_namespace": parent_id,
            "original_template": original,
            "resolved_template": resolved,
            "resolved_components": resolved_components,
            "components_used": list(resolved_components.keys()),
        }

    async def resolve_template_and_format_input(
        self, namespace: str, name: str, kwargs: Dict[str, Any]
    ) -> Dict[str, str]:
        """Combined: resolve a template + format its prompt_input with kwargs."""
        template = await self.get_template_by_natural_key(namespace, name)
        if template is None:
            raise ValueError(
                f"Template '{name}' not found in namespace '{namespace}'"
            )

        resolved = await self._resolve_loaded_template(namespace, template)

        prompt_input_template = template.get("prompt_input", "")
        try:
            input_prompt = prompt_input_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(
                f"Missing required keyword argument for template '{name}': {e}"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Error formatting input prompt for template '{name}': {e}"
            ) from e

        return {
            "resolved_template": resolved["resolved_template"],
            "input_prompt": input_prompt,
        }


class PromptComponentV2Business:
    """Business logic for the V2 prompt component service."""

    def __init__(self, service: UnifiedDataService) -> None:
        self._service = service

    async def get_component_by_natural_key(
        self, parent_id: str, component_type: str, component_name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single component by its compound natural-key."""
        results = await self._service.search(
            DataSourceQuery(
                filters={
                    "parent_id": parent_id,
                    "component_type": component_type,
                    "component_name": component_name,
                },
                limit=1,
            )
        )
        if not results:
            return None
        return _entity_to_dict(results[0])
