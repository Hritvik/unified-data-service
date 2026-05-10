"""V2 business-logic classes for prompt_registry.

Wired through ``business_logic_class`` on the V2 ServiceConfig YAMLs;
ServiceFactory injects the per-entity ``UnifiedDataService`` into each
business class' constructor and binds the instance to ``service.business``.
The auto-generated controller's custom endpoints reach these methods via
``service_method: "business.<method>"``.

Two business classes:
  - PromptTemplateV2Business: natural-key fetch + template resolution
    (placeholder substitution against components in the same namespace).
  - PromptComponentV2Business: natural-key fetch by
    (parent_id, component_type, component_name).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from common_utils.logger import get_logger
from common_utils.unified_data.factories.service_factory import ServiceFactory
from common_utils.unified_data.interfaces import DataSourceQuery
from common_utils.unified_data.service import UnifiedDataService

logger = get_logger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def _entity_to_dict(entity: Any) -> Dict[str, Any]:
    """Serialize an entity to a JSON-friendly dict.

    ``mode="json"`` coerces non-JSON-native types (PydanticObjectId, datetime,
    Enum) up front — without it, FastAPI/pydantic_core fails when the dict is
    later returned through an HTTP response."""
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
        self._component_service_name = "prompt-component-v2"

    async def get_template_by_natural_key(
        self, parent_id: str, name: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single template by its natural-key tuple
        (parent_id namespace + template name). Returns None if missing."""
        results = await self._service.search(
            DataSourceQuery(filters={"parent_id": parent_id, "name": name}, limit=1)
        )
        if not results:
            return None
        return _entity_to_dict(results[0])

    async def resolve_template(
        self, parent_id: str, name: str
    ) -> Dict[str, Any]:
        """Resolve a template by substituting `{type.name}` placeholders
        with the content of the matching components in the same namespace.

        Raises ValueError if the template is missing or any of its
        component refs cannot be resolved (matching legacy semantics in
        ``prompt_template_service.resolve_template`` at line 191).
        """
        template = await self.get_template_by_natural_key(parent_id, name)
        if template is None:
            raise ValueError(
                f"Template '{name}' not found in namespace '{parent_id}'"
            )
        return await self._resolve_loaded_template(parent_id, template)

    async def _resolve_loaded_template(
        self, parent_id: str, template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve an already-fetched template dict. Lets callers that
        already have the document avoid a second DB read."""
        component_service = ServiceFactory.get_service(self._component_service_name)
        if component_service is None:
            raise ValueError(
                f"Component service '{self._component_service_name}' is not registered"
            )

        original = template.get("template", "")
        resolved = original
        resolved_components: Dict[str, Dict[str, Any]] = {}
        unresolved: list[str] = []

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
            if component.get("component_type") != ctype:
                unresolved.append(
                    f"{ref} (type mismatch: expected {ctype}, found {component.get('component_type')})"
                )
                continue
            resolved_components[ref] = {
                "content": component.get("content"),
                "component_name": component.get("component_name"),
                "component_type": component.get("component_type"),
            }
            resolved = resolved.replace(f"{{{ref}}}", component.get("content", ""))

        # Catch any `{type.name}` placeholders in the *original* template that
        # weren't resolved. Scanning `resolved` would also flag braces inside
        # injected component content (which is free-form text and may legally
        # contain `{...}` like format specifiers).
        leftover_seen: set = set()
        for placeholder in _PLACEHOLDER_RE.findall(original):
            if placeholder in resolved_components or placeholder in leftover_seen:
                continue
            leftover_seen.add(placeholder)
            if not any(placeholder == u or u.startswith(f"{placeholder} ") for u in unresolved):
                unresolved.append(placeholder)

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
        """Combined: resolve a template + format its prompt_input with kwargs.

        Mirrors the legacy ``PromptTemplateService.resolve_template_and_format_input``
        contract. Returns ``{"resolved_template": str, "input_prompt": str}`` so
        callers can keep building ``TemplateResolutionOutput`` themselves (avoids
        a circular dependency on common_utils.models.prompt_registry from the
        unified-data layer).

        Raises ValueError on missing template, unresolved components, missing
        kwargs, or formatting failure.
        """
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
        except (TypeError, IndexError) as e:
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
        """Fetch a single component by its compound natural-key
        (parent_id namespace + component_type + component_name)."""
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
