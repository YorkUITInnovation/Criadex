import uuid

import pytest
from httpx import Response

from app.controllers.groups.about import GroupAboutResponse
from app.controllers.groups.create import GroupCreateResponse
from app.controllers.groups.delete import GroupDeleteResponse
from app.controllers.groups.query import GroupQueryResponse
from criadex.schemas import PartialGroupConfig
from criadex.index.schemas import SearchConfig
from .utils.test_client import CriaTestClient, assert_response_shape


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
                    json=test_payload.model_dump()    )

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

@pytest.mark.asyncio
async def test_groups_query_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_llm_id: int,
        sample_embedding_id: int,
        sample_reranker_id: int,
        mock_elasticsearch_client # Added this argument

) -> None:
    """
    Test the /groups/{group_name}/query route.
    """

    test_group: str = "pytest-query-" + str(uuid.uuid4())
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
        json=test_payload.model_dump()
    )
    assert response.status_code == 200, "Failed to create test group for query test"

    # Manually add mock documents to mock_elasticsearch_client._data for the test group
    mock_elasticsearch_client._data[test_group] = {
        "doc1": {
            "text": "Paris is the capital of France.",
            "metadata": {"source": "wiki", "updated_at": 1}
        },
        "doc2": {
            "text": "France is in Europe.",
            "metadata": {"source": "wiki", "updated_at": 2}
        },
        "doc3": {
            "text": "The Eiffel Tower is in Paris.",
            "metadata": {"source": "travel", "updated_at": 3}
        }
    }

    # (2) Perform a query
    query_payload = {
        "query": "What is the capital of France?",
        "top_k": 5
    }
    response: Response = client.post(
        f"/groups/{test_group}/query",
        headers=sample_master_headers,
        json=query_payload
    )

    response_data: GroupQueryResponse = assert_response_shape(response.json(), custom_shape=GroupQueryResponse)

    # Run checks on the response
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to query the test group"
    assert "nodes" in response_data.model_dump(), "Response should contain 'nodes' field"
    assert isinstance(response_data.nodes, list), "Results should be a list"
    assert len(response_data.nodes) == 3, "Results should contain 3 documents"
    assert response_data.nodes[0].node.text == "The Eiffel Tower is in Paris."
    assert response_data.nodes[1].node.text == "France is in Europe."
    assert response_data.nodes[2].node.text == "Paris is the capital of France."

    # (3) Delete the test group
    response: Response = client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
    assert response.status_code == 200, "Failed to delete test group after query test"

@pytest.mark.asyncio
async def test_groups_negative_duplicate(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_llm_id: int,
        sample_embedding_id: int,
        sample_reranker_id: int
) -> None:
    """
    Test that creating a group with a duplicate name fails.
    """
    test_group: str = "pytest-" + str(uuid.uuid4())
    test_payload: PartialGroupConfig = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=sample_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id
    )

    # Create the test group
    client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=test_payload.model_dump()
    )

    # Try to create it again
    response: Response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=test_payload.model_dump()
    )

    response_data: GroupCreateResponse = assert_response_shape(response.json(), custom_shape=GroupCreateResponse, require_status=None, require_code=None)

    assert response_data.status == 409
    assert response_data.code == "DUPLICATE"

    # cleanup
    client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)