import pytest
import uuid
from httpx import Response

from app.controllers.schemas import APIResponse, SUCCESS, ERROR, MODEL_NOT_FOUND
from app.controllers.models.cohere_models.schemas import CohereRerankRequest, CohereRerankResponse
from criadex.index.ragflow_objects.embedder import RagflowEmbedder
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