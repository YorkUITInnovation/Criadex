import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import Response

from app.controllers.groups.create import GroupCreateResponse
from criadex.schemas import PartialGroupConfig
from test.utils.test_client import CriaTestClient, assert_response_shape


@pytest.mark.asyncio
async def test_exists_model_checks_all_registries(client: CriaTestClient) -> None:
    criadex = client.app.criadex
    original_azure = criadex.exists_azure_model
    original_cohere = criadex.exists_cohere_model
    original_generic = criadex.exists_generic_model

    try:
        criadex.exists_azure_model = AsyncMock(return_value=False)
        criadex.exists_cohere_model = AsyncMock(return_value=False)
        criadex.exists_generic_model = AsyncMock(return_value=True)

        assert await criadex.exists_model(42) is True
        criadex.exists_generic_model.assert_awaited_once_with(42)

        criadex.exists_azure_model = AsyncMock(return_value=True)
        criadex.exists_cohere_model = AsyncMock(return_value=False)
        criadex.exists_generic_model = AsyncMock(return_value=False)

        assert await criadex.exists_model(7) is True
        criadex.exists_azure_model.assert_awaited_once_with(7)
        criadex.exists_generic_model.assert_not_called()

        criadex.exists_azure_model = AsyncMock(return_value=False)
        criadex.exists_cohere_model = AsyncMock(return_value=False)
        criadex.exists_generic_model = AsyncMock(return_value=False)

        assert await criadex.exists_model(0) is False
        assert await criadex.exists_model(-1) is False
    finally:
        criadex.exists_azure_model = original_azure
        criadex.exists_cohere_model = original_cohere
        criadex.exists_generic_model = original_generic


@pytest.mark.asyncio
async def test_group_create_accepts_generic_llm_model(
    client: CriaTestClient,
    sample_master_headers: dict,
    sample_embedding_id: int,
    sample_reranker_id: int,
) -> None:
    provider_type = "ollama"
    create_body = {
        "api_base_url": "http://ollama:11434",
        "api_key": "pytest-group-key",
        "api_model": f"llama3-group-{uuid.uuid4().hex[:8]}",
    }
    create_response = client.post(
        f"/models/{provider_type}/create",
        headers=sample_master_headers,
        json=create_body,
    )
    create_json = create_response.json()
    assert create_json.get("status") == 200
    generic_llm_id = create_json["model"]["id"]

    test_group = "pytest-generic-llm-" + str(uuid.uuid4())
    payload = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=generic_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id,
    )

    try:
        response: Response = client.post(
            f"/groups/{test_group}/create",
            headers=sample_master_headers,
            json=payload.model_dump(),
        )
        response_data: GroupCreateResponse = assert_response_shape(
            response.json(),
            custom_shape=GroupCreateResponse,
        )
        assert response_data.status == 200
        assert response_data.code == "SUCCESS"
        assert response_data.config.llm_model_id == generic_llm_id
    finally:
        client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
        client.delete(
            f"/models/{provider_type}/{generic_llm_id}/delete",
            headers=sample_master_headers,
        )


@pytest.mark.asyncio
async def test_group_create_rejects_unknown_model(
    client: CriaTestClient,
    sample_master_headers: dict,
    sample_embedding_id: int,
    sample_reranker_id: int,
) -> None:
    test_group = "pytest-invalid-model-" + str(uuid.uuid4())
    payload = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=999999,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id,
    )

    response: Response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=payload.model_dump(),
    )
    response_data: GroupCreateResponse = assert_response_shape(
        response.json(),
        custom_shape=GroupCreateResponse,
        require_status=400,
        require_code="INVALID_MODEL",
    )
    assert response_data.status == 400
    assert response_data.code == "INVALID_MODEL"
