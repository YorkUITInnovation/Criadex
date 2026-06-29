from unittest.mock import AsyncMock, patch

import pytest

from criadex.index.ragflow_objects import model_ids


def test_is_qualified_ragflow_model_id() -> None:
    assert model_ids.is_qualified_ragflow_model_id("gpt-3.5-turbo@personal@OpenAI")
    assert not model_ids.is_qualified_ragflow_model_id("gpt-3.5-turbo@OpenAI")
    assert not model_ids.is_qualified_ragflow_model_id("gpt-3.5-turbo")


@pytest.mark.asyncio
async def test_resolve_qualified_model_id_returns_already_qualified_value() -> None:
    qualified = "gpt-5@instance@OpenAI"
    result = await model_ids.resolve_qualified_model_id(
        api_model=qualified,
        model_kind="chat",
        tenant_id="tenant-1",
    )
    assert result == qualified


@pytest.mark.asyncio
async def test_resolve_qualified_model_id_matches_tenant_default(monkeypatch) -> None:
    monkeypatch.setattr(
        model_ids,
        "resolve_tenant_default_model_id",
        AsyncMock(return_value="embed-english-v2.0@cohere@Cohere"),
    )

    result = await model_ids.resolve_qualified_model_id(
        api_model="embed-english-v2.0",
        llm_factory="Cohere",
        model_kind="embedding",
        tenant_id="tenant-1",
    )
    assert result == "embed-english-v2.0@cohere@Cohere"


@pytest.mark.asyncio
async def test_resolve_qualified_model_id_returns_none_when_unresolved(monkeypatch) -> None:
    monkeypatch.setattr(model_ids, "resolve_tenant_id", AsyncMock(return_value="tenant-1"))
    monkeypatch.setattr(model_ids, "resolve_tenant_default_model_id", AsyncMock(return_value=None))
    monkeypatch.setattr(model_ids, "_lookup_provider_model_id", AsyncMock(return_value=None))

    result = await model_ids.resolve_qualified_model_id(
        api_model="unknown-model",
        llm_factory="Vendor",
        model_kind="chat",
    )
    assert result is None


@pytest.mark.asyncio
async def test_resolve_tenant_id_prefers_env(monkeypatch) -> None:
    monkeypatch.setattr(model_ids, "RAGFLOW_TENANT_ID", "env-tenant")
    result = await model_ids.resolve_tenant_id(api_key="ignored")
    assert result == "env-tenant"
