import pytest
from criadex.agent.azure.transform import TransformAgent

def test_transform_agent_transform():
    # Given
    agent = TransformAgent()
    text = "This is a test sentence."

    # When
    response = agent.transform(text)

    # Then
    assert response.transformed_text == "THIS IS A TEST SENTENCE."
