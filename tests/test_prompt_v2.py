"""Tests for prompt_registry V2 business classes — resolve_template and
compound natural-key lookups."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

import pytest

from common_utils.unified_data.business.prompt_v2 import (
    PromptComponentV2Business,
    PromptTemplateV2Business,
)
from common_utils.unified_data.factories.service_factory import ServiceFactory
from common_utils.unified_data.interfaces import DataSourceQuery


class FakeUDS:
    """Tiny stand-in for UnifiedDataService — only the methods our
    business classes touch (search) are implemented."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        entity = dict(data)
        entity.setdefault("id", uuid.uuid4().hex)
        self._store[entity["id"]] = entity
        return entity

    async def search(self, query: DataSourceQuery) -> List[Dict[str, Any]]:
        items = list(self._store.values())
        if query.filters:
            items = [
                e
                for e in items
                if all(e.get(k) == v for k, v in query.filters.items())
            ]
        if query.limit is not None:
            items = items[: query.limit]
        return items


@pytest.fixture(autouse=True)
def reset_service_factory():
    """ServiceFactory uses a class-level registry. Clear it around each
    test so PromptTemplateV2Business can resolve `prompt-component-v2`."""
    ServiceFactory.clear_registry()
    yield
    ServiceFactory.clear_registry()


@pytest.mark.asyncio
async def test_get_template_by_natural_key_hits_and_misses():
    template_svc = FakeUDS()
    biz = PromptTemplateV2Business(template_svc)

    await template_svc.create(
        {
            "parent_id": "ns_a",
            "name": "greet",
            "template": "hello",
            "prompt_input": "x",
            "components": [],
        }
    )

    found = await biz.get_template_by_natural_key("ns_a", "greet")
    assert found is not None
    assert found["template"] == "hello"

    missing = await biz.get_template_by_natural_key("ns_b", "greet")
    assert missing is None


@pytest.mark.asyncio
async def test_resolve_template_substitutes_placeholders_in_namespace():
    template_svc = FakeUDS()
    component_svc = FakeUDS()
    ServiceFactory._service_registry["prompt-component-v2"] = component_svc

    await template_svc.create(
        {
            "parent_id": "ns_a",
            "name": "greet",
            "template": "{header.welcome} world {footer.bye}",
            "prompt_input": "x",
            "components": ["header.welcome", "footer.bye"],
        }
    )
    await component_svc.create(
        {
            "parent_id": "ns_a",
            "component_type": "header",
            "component_name": "welcome",
            "content": "Hi",
        }
    )
    await component_svc.create(
        {
            "parent_id": "ns_a",
            "component_type": "footer",
            "component_name": "bye",
            "content": "Bye",
        }
    )
    # Decoy in another namespace — must NOT be picked.
    await component_svc.create(
        {
            "parent_id": "ns_b",
            "component_type": "header",
            "component_name": "welcome",
            "content": "WRONG",
        }
    )

    biz = PromptTemplateV2Business(template_svc)
    out = await biz.resolve_template("ns_a", "greet")

    assert out["resolved_template"] == "Hi world Bye"
    assert out["original_template"] == "{header.welcome} world {footer.bye}"
    assert set(out["resolved_components"].keys()) == {
        "header.welcome",
        "footer.bye",
    }
    assert out["resolved_components"]["header.welcome"]["content"] == "Hi"


@pytest.mark.asyncio
async def test_resolve_template_raises_on_missing_template():
    biz = PromptTemplateV2Business(FakeUDS())
    ServiceFactory._service_registry["prompt-component-v2"] = FakeUDS()
    with pytest.raises(ValueError, match="not found in namespace"):
        await biz.resolve_template("ns_a", "missing")


@pytest.mark.asyncio
async def test_resolve_template_raises_on_unresolved_components():
    template_svc = FakeUDS()
    component_svc = FakeUDS()
    ServiceFactory._service_registry["prompt-component-v2"] = component_svc

    await template_svc.create(
        {
            "parent_id": "ns_a",
            "name": "greet",
            "template": "{header.welcome}",
            "prompt_input": "x",
            "components": ["header.welcome"],
        }
    )
    # Component intentionally missing.

    biz = PromptTemplateV2Business(template_svc)
    with pytest.raises(ValueError, match="Could not resolve"):
        await biz.resolve_template("ns_a", "greet")


@pytest.mark.asyncio
async def test_get_component_by_natural_key():
    component_svc = FakeUDS()
    biz = PromptComponentV2Business(component_svc)

    await component_svc.create(
        {
            "parent_id": "ns_a",
            "component_type": "header",
            "component_name": "hi",
            "content": "Hello",
        }
    )

    hit = await biz.get_component_by_natural_key("ns_a", "header", "hi")
    assert hit is not None and hit["content"] == "Hello"

    miss = await biz.get_component_by_natural_key("ns_a", "header", "nope")
    assert miss is None
