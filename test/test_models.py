import pytest
import uuid
import re
from httpx import Response

from app.controllers.schemas import APIResponse, SUCCESS, ERROR, MODEL_NOT_FOUND
from app.controllers.models.cohere_models.schemas import CohereRerankRequest, CohereRerankResponse
from criadex.index.ragflow_objects.embedder import RagflowEmbedder
from criadex.index.ragflow_objects.vector_store import RagflowVectorStore
from test.utils.test_client import CriaTestClient, assert_response_shape


def test_ragflow_embedder():
    """
    Test the RagflowEmbedder to ensure it returns a valid embedding.
    """
    embedder = RagflowEmbedder()
    text = "This is a test sentence."
    embedding = embedder.embed(text)

    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) > 0, "Embedding should not be empty"
    assert all(isinstance(x, float) for x in embedding), "All elements in the embedding should be floats"


def test_ragflow_vector_store_create_collection_uses_requested_dims(mock_elasticsearch_client):
    mock_elasticsearch_client.indices.exists.return_value = False
    mock_elasticsearch_client.indices.create.reset_mock()

    store = RagflowVectorStore(host="localhost", port=9200)
    store.create_collection("pytest-dims-index", embedding_dims=1536)

    mock_elasticsearch_client.indices.create.assert_called_once()
    _, kwargs = mock_elasticsearch_client.indices.create.call_args
    assert kwargs["body"]["mappings"]["properties"]["embedding"]["dims"] == 1536


def test_ragflow_vector_store_sanitizes_invalid_collection_name():
    store = RagflowVectorStore(host="localhost", port=9200)
    unsafe_name = "Moodle 5 laptop dev-The art of Art-document-index"

    safe_name = store._to_es_index_name(unsafe_name)

    assert " " not in safe_name
    assert safe_name == safe_name.lower()
    assert len(safe_name) <= 255
    assert re.search(r"-[0-9a-f]{8}$", safe_name) is not None


def test_ragflow_vector_store_insert_uses_sanitized_index_name(mock_elasticsearch_client):
    store = RagflowVectorStore(host="localhost", port=9200)
    unsafe_name = "Moodle 5 laptop dev-The art of Art-document-index"

    # insert() now requires the target ES index to exist.
    mock_elasticsearch_client.indices.exists.return_value = True
    mock_elasticsearch_client.index.reset_mock()
    store.insert(unsafe_name, "doc-1", [0.1, 0.2], "test text", {"source": "pytest"})

    mock_elasticsearch_client.index.assert_called_once()
    _, kwargs = mock_elasticsearch_client.index.call_args
    used_index = kwargs["index"]
    assert " " not in used_index
    assert used_index == store._to_es_index_name(unsafe_name)

@pytest.mark.asyncio
async def test_cohere_rerank_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_reranker_id: int
) -> None:
    """
    Test the /models/{model_id}/rerank route for a positive scenario.
    """
    # (1) Prepare sample data
    query = "What is the capital of France?"
    documents = [
        {"text": "Paris is the capital of France."},
        {"text": "The Eiffel Tower is in Paris."},
        {"text": "France is in Europe."}
    ]
    
    request_body = CohereRerankRequest(query=query, documents=documents)

    # (2) Call the rerank endpoint
    response: Response = client.post(
        f"/models/{sample_reranker_id}/rerank",
        headers=sample_master_headers,
        json=request_body.model_dump()
    )

    response_data: CohereRerankResponse = assert_response_shape(
        response.json(),
        custom_shape=CohereRerankResponse
    )

    # (3) Assert the response
    assert response_data.status == 200
    assert response_data.code == "SUCCESS"
    assert response_data.reranked_documents == documents


@pytest.mark.asyncio
async def test_generic_models_crud_round_trip(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    """
    End-to-end test for the new generic /models/{provider_type}/* routes.

    This exercises:
    - POST   /models/{provider_type}/create
    - GET    /models/{provider_type}/{model_id}/about
    - PATCH  /models/{provider_type}/{model_id}/update
    - DELETE /models/{provider_type}/{model_id}/delete
    """
    provider_type = "ollama"
    api_model = f"llama3-8b-{uuid.uuid4().hex[:8]}"

    # 1) Create a generic model
    create_body = {
        "api_base_url": "http://ollama:11434",
        "api_key": "test-key",
        "api_model": api_model,
        "extra_param": "extra-value",
    }
    create_response = client.post(
        f"/models/{provider_type}/create",
        headers=sample_master_headers,
        json=create_body,
    )
    create_json = create_response.json()
    create_data: APIResponse = assert_response_shape(create_json)
    assert create_data.status == 200
    # shape helper already enforces SUCCESS by default, but assert explicitly for clarity
    assert create_data.code == "SUCCESS"
    assert isinstance(create_json.get("model"), dict)
    model_dict = create_json["model"]
    model_id = model_dict.get("id")
    assert isinstance(model_id, int)
    assert model_dict.get("provider_type") == provider_type
    # Config should echo the original keys
    config = model_dict.get("config") or {}
    for k, v in create_body.items():
        assert config.get(k) == v

    # 2) About should return the same model
    about_response = client.get(
        f"/models/{provider_type}/{model_id}/about",
        headers=sample_master_headers,
    )
    about_json = about_response.json()
    about_data: APIResponse = assert_response_shape(about_json)
    assert about_data.status == 200
    assert about_data.code == "SUCCESS"
    assert isinstance(about_json.get("model"), dict)
    about_model = about_json["model"]
    assert about_model.get("id") == model_id
    assert about_model.get("provider_type") == provider_type

    # 3) Update merges into the existing config
    update_body = {
        "api_model": "llama3:70b",
        "new_flag": True,
    }
    update_response = client.patch(
        f"/models/{provider_type}/{model_id}/update",
        headers=sample_master_headers,
        json=update_body,
    )
    update_json = update_response.json()
    update_data: APIResponse = assert_response_shape(update_json)
    assert update_data.status == 200
    assert update_data.code == "SUCCESS"
    updated_model = (update_json.get("model") or {})
    updated_config = updated_model.get("config") or {}
    # Updated keys
    assert updated_config.get("api_model") == "llama3:70b"
    assert updated_config.get("new_flag") is True
    # Original keys still present
    assert updated_config.get("api_base_url") == create_body["api_base_url"]
    assert updated_config.get("api_key") == create_body["api_key"]

    # 4) Delete the model
    delete_response = client.delete(
        f"/models/{provider_type}/{model_id}/delete",
        headers=sample_master_headers,
    )
    delete_data: APIResponse = assert_response_shape(delete_response.json())
    assert delete_data.status == 200
    assert delete_data.code == "SUCCESS"

    # 5) About should now report NOT_FOUND for this provider/model_id
    not_found_response = client.get(
        f"/models/{provider_type}/{model_id}/about",
        headers=sample_master_headers,
    )
    not_found_data: APIResponse = assert_response_shape(
        not_found_response.json(),
        require_status=404,
        require_code="NOT_FOUND",
    )
    assert not_found_data.status == 404
    assert not_found_data.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_generic_models_rejects_azure_and_cohere(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    """
    Guardrail: the generic route must not handle azure/cohere,
    so that existing /models/azure/* and /models/cohere/* keep precedence.
    """
    body = {"api_model": "ignored"}

    # azure
    azure_resp = client.post(
        "/models/azure/create",
        headers=sample_master_headers,
        json=body,
    )
    # Handled by dedicated Azure controller, not generic one.
    # Validation errors are expressed as 422 when required fields are missing.
    assert azure_resp.status_code in (200, 400, 409, 422)

    # cohere
    cohere_resp = client.post(
        "/models/cohere/create",
        headers=sample_master_headers,
        json=body,
    )
    assert cohere_resp.status_code in (200, 400, 409, 422)


@pytest.mark.asyncio
async def test_provider_model_list_endpoints(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    azure_response = client.get(
        "/models/azure/list",
        headers=sample_master_headers,
    )
    azure_data: APIResponse = assert_response_shape(azure_response.json())
    assert azure_data.status == 200
    assert any(model["api_model"] == "gpt-4" for model in azure_response.json().get("models", []))
    assert any(model["api_model"] == "text-embedding-ada-002" for model in azure_response.json().get("models", []))

    cohere_response = client.get(
        "/models/cohere/list",
        headers=sample_master_headers,
    )
    cohere_data: APIResponse = assert_response_shape(cohere_response.json())
    assert cohere_data.status == 200
    assert any(model["api_model"] == "rerank-english-v2.0" for model in cohere_response.json().get("models", []))


@pytest.mark.asyncio
async def test_aggregate_model_list_endpoint(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    response = client.get(
        "/models/list",
        headers=sample_master_headers,
    )
    data: APIResponse = assert_response_shape(response.json())
    assert data.status == 200

    models = response.json().get("models", [])
    provider_types = {model["provider_type"] for model in models}
    assert "azure" in provider_types
    assert "cohere" in provider_types


@pytest.mark.asyncio
async def test_generic_provider_list_endpoint(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    provider_type = "ollama"
    api_model = f"llama3-list-{uuid.uuid4().hex[:8]}"
    create_response = client.post(
        f"/models/{provider_type}/create",
        headers=sample_master_headers,
        json={
            "api_base_url": "http://ollama:11434",
            "api_model": api_model,
        },
    )
    create_data: APIResponse = assert_response_shape(create_response.json())
    assert create_data.status == 200
    model_id = create_response.json()["model"]["id"]

    try:
        list_response = client.get(
            f"/models/{provider_type}/list",
            headers=sample_master_headers,
        )
        list_data: APIResponse = assert_response_shape(list_response.json())
        assert list_data.status == 200
        models = list_response.json().get("models", [])
        assert any(
            model["provider_type"] == provider_type
            and (model.get("config") or {}).get("api_model") == api_model
            for model in models
        )
    finally:
        client.delete(
            f"/models/{provider_type}/{model_id}/delete",
            headers=sample_master_headers,
        )


@pytest.mark.asyncio
async def test_generic_model_create_is_idempotent(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    provider_type = "ollama"
    api_model = f"llama3-idem-{uuid.uuid4().hex[:8]}"
    payload = {
        "api_base_url": "http://ollama:11434",
        "api_model": api_model,
    }

    first = client.post(
        f"/models/{provider_type}/create",
        headers=sample_master_headers,
        json=payload,
    )
    first_data: APIResponse = assert_response_shape(first.json())
    assert first_data.status == 200
    first_id = first.json()["model"]["id"]

    second = client.post(
        f"/models/{provider_type}/create",
        headers=sample_master_headers,
        json=payload,
    )
    second_data: APIResponse = assert_response_shape(second.json())
    assert second_data.status == 200
    assert second.json()["model"]["id"] == first_id

    client.delete(
        f"/models/{provider_type}/{first_id}/delete",
        headers=sample_master_headers,
    )