import uuid
import json

import pytest
from httpx import Response
from unittest.mock import AsyncMock

from app.controllers.groups.about import GroupAboutResponse
from app.controllers.groups.create import GroupCreateResponse
from app.controllers.groups.delete import GroupDeleteResponse
from app.controllers.groups.graph import GraphBuildResponse, GraphSearchResponse, GraphStatusResponse
from app.controllers.groups.query import GroupQueryResponse
from criadex.index.base_api import ContentUploadConfig
from criadex.schemas import PartialGroupConfig
from criadex.index.schemas import SearchConfig
from .utils.content_utils import sample_document
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


@pytest.mark.asyncio
async def test_groups_query_negative(
    client: CriaTestClient,
    sample_master_headers: dict
) -> None:
    """
    Test the /groups/{group_name}/query route for negative scenarios.
    """
    non_existent_group: str = "pytest-non-existent-" + str(uuid.uuid4())

    # (1) Perform a query on a non-existent group
    query_payload = {
        "query": "What is the capital of France?",
        "top_k": 5
    }
    response: Response = client.post(
        f"/groups/{non_existent_group}/query",
        headers=sample_master_headers,
        json=query_payload
    )

    response_data: GroupQueryResponse = assert_response_shape(response.json(), custom_shape=GroupQueryResponse, require_status=None, require_code=None)

    # Run checks on the response
    assert response_data.status == 404
    assert response_data.code == "GROUP_NOT_FOUND"
    assert response_data.nodes == []
    assert response_data.assets == []
    assert response_data.search_units == 0


@pytest.mark.asyncio
async def test_groups_graph_routes_positive(
    client: CriaTestClient,
    sample_master_headers: dict,
    sample_llm_id: int,
    sample_embedding_id: int,
    sample_reranker_id: int,
    mock_elasticsearch_client
) -> None:
    test_group: str = "pytest-graph-" + str(uuid.uuid4())
    test_payload: PartialGroupConfig = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=sample_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id
    )

    response: Response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=test_payload.model_dump()
    )
    assert response.status_code == 200, "Failed to create test group for graph routes test"

    mock_elasticsearch_client._data[test_group] = {
        "doc1": {
            "text": "Midterm and final exam policy for computer science.",
            "metadata": {"source": "syllabus", "updated_at": 1}
        },
        "doc2": {
            "text": "Assignment weighting and quiz grading rubric for students.",
            "metadata": {"source": "syllabus", "updated_at": 2}
        },
    }

    status_response = client.get(f"/groups/{test_group}/graph_status", headers=sample_master_headers)
    status_data: GraphStatusResponse = assert_response_shape(
        status_response.json(),
        custom_shape=GraphStatusResponse
    )
    assert status_data.status == 200
    assert status_data.graph.status in {"NOT_BUILT", "QUEUED"}

    build_response = client.post(f"/groups/{test_group}/build_graph", headers=sample_master_headers)
    build_data: GraphBuildResponse = assert_response_shape(
        build_response.json(),
        custom_shape=GraphBuildResponse
    )
    assert build_data.status == 200
    assert build_data.job_id is not None
    assert build_data.state in {"QUEUED", "RUNNING", "READY"}

    status_response_after_build = client.get(f"/groups/{test_group}/graph_status", headers=sample_master_headers)
    status_data_after_build: GraphStatusResponse = assert_response_shape(
        status_response_after_build.json(),
        custom_shape=GraphStatusResponse
    )
    assert status_data_after_build.status == 200
    assert status_data_after_build.graph.status in {"QUEUED", "RUNNING", "READY"}

    graph_query_payload = {
        "query": "How is exam grading calculated?",
        "top_k": 3,
        "max_hops": 2,
        "max_expansion_terms": 5,
        "auto_build": False
    }
    search_response = client.post(
        f"/groups/{test_group}/graph_search",
        headers=sample_master_headers,
        json=graph_query_payload
    )
    search_data: GraphSearchResponse = assert_response_shape(
        search_response.json(),
        custom_shape=GraphSearchResponse
    )
    assert search_data.status == 200
    assert isinstance(search_data.nodes, list)
    assert "source" in search_data.graph_metadata

    delete_response = client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
    assert delete_response.status_code == 200, "Failed to delete test group after graph routes test"


@pytest.mark.asyncio
async def test_groups_graph_routes_negative_not_found(
    client: CriaTestClient,
    sample_master_headers: dict
) -> None:
    missing_group = "pytest-graph-missing-" + str(uuid.uuid4())

    build_response = client.post(f"/groups/{missing_group}/build_graph", headers=sample_master_headers)
    build_data: GraphBuildResponse = assert_response_shape(
        build_response.json(),
        custom_shape=GraphBuildResponse,
        require_status=None,
        require_code=None
    )
    assert build_data.status == 404
    assert build_data.code == "GROUP_NOT_FOUND"

    status_response = client.get(f"/groups/{missing_group}/graph_status", headers=sample_master_headers)
    status_data: GraphStatusResponse = assert_response_shape(
        status_response.json(),
        custom_shape=GraphStatusResponse,
        require_status=None,
        require_code=None
    )
    assert status_data.status == 404
    assert status_data.code == "GROUP_NOT_FOUND"

    search_response = client.post(
        f"/groups/{missing_group}/graph_search",
        headers=sample_master_headers,
        json={"query": "hello", "top_k": 2}
    )
    search_data: GraphSearchResponse = assert_response_shape(
        search_response.json(),
        custom_shape=GraphSearchResponse,
        require_status=None,
        require_code=None
    )
    assert search_data.status == 404
    assert search_data.code == "GROUP_NOT_FOUND"


@pytest.mark.asyncio
async def test_groups_graph_search_auto_build_edge_empty_index(
    client: CriaTestClient,
    sample_master_headers: dict,
    sample_llm_id: int,
    sample_embedding_id: int,
    sample_reranker_id: int,
) -> None:
    test_group: str = "pytest-graph-empty-" + str(uuid.uuid4())
    test_payload: PartialGroupConfig = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=sample_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id
    )
    create_response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=test_payload.model_dump()
    )
    assert create_response.status_code == 200

    search_response = client.post(
        f"/groups/{test_group}/graph_search",
        headers=sample_master_headers,
        json={"query": "gradebook policy", "top_k": 2, "auto_build": True}
    )
    search_data: GraphSearchResponse = assert_response_shape(
        search_response.json(),
        custom_shape=GraphSearchResponse
    )
    assert search_data.status == 200
    assert search_data.graph_metadata["source"] in {"fallback", "ragflow", "standard"}
    assert isinstance(search_data.graph_metadata["expanded_terms"], list)

    delete_response = client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
    assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_groups_graph_search_fallback_on_ragflow_error(
    client: CriaTestClient,
    sample_master_headers: dict,
    sample_llm_id: int,
    sample_embedding_id: int,
    sample_reranker_id: int,
    mock_elasticsearch_client
) -> None:
    test_group = "pytest-graph-fallback-" + str(uuid.uuid4())
    create_payload = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=sample_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id
    )
    create_response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=create_payload.model_dump()
    )
    assert create_response.status_code == 200

    mock_elasticsearch_client._data[test_group] = {
        "doc1": {"text": "Grading rubric includes quizzes and exams.", "metadata": {"updated_at": 1}},
    }

    async def ready_ragflow_status(group_name: str, job_id=None):
        return {
            "group_name": group_name,
            "graph": {
                "status": "READY",
                "source": "ragflow",
                "node_count": 1,
                "edge_count": 0,
                "top_entities": [],
                "fallback_reason": None,
                "error": None,
                "built_at": None,
                "updated_at": None,
            },
            "job": {"job_id": "job-ragflow-ready", "state": "READY", "source": "ragflow", "progress": 100},
        }

    client.app.criadex.graph_status = ready_ragflow_status

    client.app.criadex.graph_rag_client.graph_search = AsyncMock(side_effect=RuntimeError("ragflow graph unavailable"))

    search_response = client.post(
        f"/groups/{test_group}/graph_search",
        headers=sample_master_headers,
        json={"query": "How is grading weighted?", "top_k": 2, "auto_build": False}
    )
    search_data: GraphSearchResponse = assert_response_shape(
        search_response.json(),
        custom_shape=GraphSearchResponse
    )
    assert search_data.status == 200
    assert search_data.graph_metadata["source"] == "fallback"
    assert "ragflow graph unavailable" in (search_data.graph_metadata.get("fallback_reason") or "")

    delete_response = client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
    assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_groups_graph_search_auto_build_rebuilds_stale_graph(
    client: CriaTestClient,
    sample_master_headers: dict,
    sample_llm_id: int,
    sample_embedding_id: int,
    sample_reranker_id: int,
    mock_elasticsearch_client
) -> None:
    test_group = "pytest-graph-stale-" + str(uuid.uuid4())
    create_payload = PartialGroupConfig(
        type="DOCUMENT",
        llm_model_id=sample_llm_id,
        rerank_model_id=sample_reranker_id,
        embedding_model_id=sample_embedding_id
    )
    create_response = client.post(
        f"/groups/{test_group}/create",
        headers=sample_master_headers,
        json=create_payload.model_dump()
    )
    assert create_response.status_code == 200

    mock_elasticsearch_client._data[test_group] = {
        "doc1": {"text": "Course grade uses labs and final exam.", "metadata": {"updated_at": 1}},
    }

    first_build = client.post(f"/groups/{test_group}/build_graph", headers=sample_master_headers)
    first_build_data: GraphBuildResponse = assert_response_shape(first_build.json(), custom_shape=GraphBuildResponse)
    assert first_build_data.job_id is not None

    upload_payload = ContentUploadConfig(
        file_name="pytest-stale-doc-" + str(uuid.uuid4()),
        file_contents=sample_document().model_dump(),
        file_metadata={"source": "pytest-stale-rebuild"}
    )
    upload_response = client.post(
        f"/groups/{test_group}/content/upload",
        headers=sample_master_headers,
        json=json.loads(upload_payload.model_dump_json())
    )
    assert upload_response.status_code == 200

    search_response = client.post(
        f"/groups/{test_group}/graph_search",
        headers=sample_master_headers,
        json={"query": "How are final grades calculated?", "top_k": 2, "auto_build": True}
    )
    search_data: GraphSearchResponse = assert_response_shape(
        search_response.json(),
        custom_shape=GraphSearchResponse
    )
    assert search_data.status == 200
    assert search_data.graph_metadata.get("job_id") is not None
    assert search_data.graph_metadata.get("job_id") != first_build_data.job_id

    delete_response = client.delete(f"/groups/{test_group}/delete", headers=sample_master_headers)
    assert delete_response.status_code == 200
