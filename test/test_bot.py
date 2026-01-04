import pytest
from unittest.mock import AsyncMock, MagicMock
from criadex.bot.bot import Bot
from criadex.index.schemas import IndexResponse, TextNodeWithScore

@pytest.mark.asyncio
async def test_bot_search():
    """
    Test the search method of the Bot class.
    """
    # Create mock objects for the vector_store and embedder
    mock_vector_store = MagicMock()
    mock_embedder = MagicMock()

    # Configure the mock objects
    mock_embedder.embed.return_value = [0.1] * 768
    mock_vector_store.asearch = AsyncMock(
        return_value=[
            {
                '_source': {
                    'text': 'This is a test node.',
                    'metadata': {'file_name': 'test.txt'}
                }
            }
        ]
    )

    # Create a Bot instance with the mock objects
    bot = Bot(vector_store=mock_vector_store, embedder=mock_embedder)

    # Call the search method
    group_name = "test_group"
    query = "test query"
    response = await bot.search(group_name, query)

    # Assert that the embedder and vector_store methods were called with the correct arguments
    mock_embedder.embed.assert_called_once_with(query)
    mock_vector_store.asearch.assert_called_once_with(
        collection_name=group_name,
        query_embedding=[0.1] * 768,
        top_k=10,
        sort={"metadata.updated_at": {"order": "desc"}},
        query_filter=None
    )

    # Assert that the response is an IndexResponse object
    assert isinstance(response, IndexResponse)

    # Assert that the response contains the expected node
    assert len(response.nodes) == 1
    assert isinstance(response.nodes[0], TextNodeWithScore)
    assert response.nodes[0].node.text == 'This is a test node.'
    assert response.nodes[0].node.metadata == {'file_name': 'test.txt'}