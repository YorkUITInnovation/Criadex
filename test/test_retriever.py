import pytest
from unittest.mock import MagicMock
from criadex.index.ragflow_objects.retriever import RagflowRetriever


def test_ragflow_retriever():
    """
    Test the RagflowRetriever to ensure it returns a list.
    """
    # Create mock objects for the vector_store and embedder
    mock_vector_store = MagicMock()
    mock_embedder = MagicMock()

    # Create a Retriever instance with the mock objects
    retriever = RagflowRetriever(vector_store=mock_vector_store, embedder=mock_embedder)

    # Call the retrieve method
    query = "test query"
    result = retriever.retrieve(query)

    # Assert that the result is a list
    assert isinstance(result, list)
