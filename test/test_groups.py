import uuid

import pytest
from httpx import Response

from app.controllers.groups.about import GroupAboutResponse
from app.controllers.groups.create import GroupCreateResponse
from app.controllers.groups.delete import GroupDeleteResponse
from criadex.schemas import PartialGroupConfig
from utils.test_client import CriaTestClient, sample_master_headers, client, assert_response_shape, sample_llm_id, sample_reranker_id, sample_embedding_id


@pytest.mark.asyncio
async def test_groups_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_llm_id: int,
        sample_embedding_id: int,
        sample_reranker_id: int

) -> None:
    """
    Test the group-related routes:
    - /groups/{group_name}/create
    - /groups/{group_name}/about
    - /groups/{group_name}/delete

    """

    test_group: str = "pytest-" + str(uuid.uuid4())
    test_payload: PartialGroupConfig = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=sample_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id
    )

    # (1) Create the test group
    response: Response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=test_payload.dict()
    )

    response_data: GroupCreateResponse = assert_response_shape(response.json(), custom_shape=GroupCreateResponse)

    # Run checks on the response
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to create the test group"
    assert response_data.config.name == test_group, "The group name does not match the test group name"
    assert response_data.config.rerank_model_id == sample_reranker_id, "The reranker model ID does not match the sample reranker ID"
    assert response_data.config.llm_model_id == sample_llm_id, "The LLM model ID does not match the sample LLM ID"
    assert response_data.config.embedding_model_id == sample_embedding_id, "The embedding model ID does not match the sample embedding ID"
    assert response_data.config.type == test_payload.type, "The group type does not match the test group type"

    # (2) Check if the test group exists & matches the expected config
    response: Response = client.get(f"/groups/{test_group}/about", headers=sample_master_headers)
    response_data: GroupAboutResponse = assert_response_shape(response.json(), custom_shape=GroupAboutResponse)

    # Run checks on the response
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to check the test group"
    assert response_data.info.name == test_group, "The group name does not match the test group name"
    assert response_data.info.rerank_model_id == sample_reranker_id, "The reranker model ID does not match the sample reranker ID"
    assert response_data.info.llm_model_id == sample_llm_id, "The LLM model ID does not match the sample LLM ID"
    assert response_data.info.embedding_model_id == sample_embedding_id, "The embedding model ID does not match the sample embedding ID"
    assert response_data.info.type == test_payload.type, "The group type does not match the test group type"

    # (3) Delete the test group
    response: Response = client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
    response_data: GroupDeleteResponse = assert_response_shape(response.json(), custom_shape=GroupDeleteResponse)

    # Run checks on the response
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to delete the test group"

    # (4) Confirm it DNE by checking the about again
    response: Response = client.get(f"/groups/{test_group}/about", headers=sample_master_headers)
    response_data: GroupAboutResponse = assert_response_shape(response.json(), custom_shape=GroupAboutResponse, require_status=None, require_code=None)
    assert response_data.status == 404, "The test group still exists after deletion!"
