import pytest
from criadex.agent.azure.language import LanguageAgent

def test_language_agent_detect():
    # Given
    agent = LanguageAgent()
    text = "This is a test sentence in English."

    # When
    response = agent.detect(text)

    # Then
    assert response.language == "EN"
    assert response.confidence > 0.5
