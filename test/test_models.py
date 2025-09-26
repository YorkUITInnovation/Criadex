import pytest
from criadex.index.ragflow_objects.embedder import RagflowEmbedder


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
