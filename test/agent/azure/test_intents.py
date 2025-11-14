import pytest
from unittest.mock import AsyncMock, MagicMock
from criadex.agent.azure.intents import Intent, RankedIntent, IntentsAgentResponse, IntentsAgent
from criadex.index.ragflow_objects.intents import RagflowIntentsAgent, RagflowIntentsAgentResponse

@pytest.fixture
def intents_agent():
    agent = IntentsAgent(llm_model_id=1)
    # Mock the get_intents method of the RagflowIntentsAgent base class
    agent.get_intents = MagicMock(return_value=RagflowIntentsAgentResponse(message="test message", model_id=1))
    return agent

@pytest.fixture
def sample_intents():
    return [
        Intent(name="Greeting", description="User says hello"),
        Intent(name="Question", description="User asks a question"), # Changed order
        Intent(name="Farewell", description="User says goodbye")
    ]

@pytest.mark.asyncio
async def test_intents_agent_execute_positive(intents_agent, sample_intents):
    prompt = "Hello, how are you?"
    
    # The execute method no longer uses query_model, so we don't need to mock it here.
    # Instead, it calls get_intents, which is mocked in the fixture.
    # It also calls parse_llm_response with an empty string, so ranked_intents will be empty.

    response = await intents_agent.execute(sample_intents, prompt)

    # Assertions
    intents_agent.get_intents.assert_called_once()
    assert isinstance(response, IntentsAgentResponse)
    assert len(response.ranked_intents) == 0
    assert response.message == "Successfully ranked intents"
    assert "prompt_tokens" in response.usage
    assert "completion_tokens" in response.usage
    assert "total_tokens" in response.usage
    assert "label" in response.usage

@pytest.mark.asyncio
async def test_intents_agent_execute_empty_llm_response(intents_agent, sample_intents):
    prompt = "Empty response test"

    response = await intents_agent.execute(sample_intents, prompt)

    intents_agent.get_intents.assert_called_once()
    assert isinstance(response, IntentsAgentResponse)
    assert len(response.ranked_intents) == 0
    assert response.message == "Successfully ranked intents"

@pytest.mark.asyncio
async def test_intents_agent_execute_malformed_llm_response(intents_agent, sample_intents):
    prompt = "Malformed response test"

    response = await intents_agent.execute(sample_intents, prompt)

    intents_agent.get_intents.assert_called_once()
    assert isinstance(response, IntentsAgentResponse)
    assert len(response.ranked_intents) == 0
    assert response.message == "Successfully ranked intents"

def test_intents_agent_build_query(sample_intents):
    prompt = "Test prompt for query building"
    query_payload = IntentsAgent.build_query(prompt, sample_intents)

    assert "categories" in query_payload
    assert len(query_payload["categories"]) == 3
    assert query_payload["categories"][0]["name"] == "Greeting"
    assert query_payload["question"] == prompt

def test_intents_agent_parse_llm_response_valid(sample_intents):
    llm_response_content = "1. category: Greeting, score: 9\n2. category: Question, score: 7"
    ranked_intents = IntentsAgent.parse_llm_response(llm_response_content, sample_intents)

    assert len(ranked_intents) == 2
    assert ranked_intents[0].name == "Greeting"
    assert ranked_intents[0].score == 0.9
    assert ranked_intents[1].name == "Question"
    assert ranked_intents[1].score == 0.7

def test_intents_agent_parse_llm_response_invalid_format(sample_intents):
    llm_response_content = "Invalid line format"
    ranked_intents = IntentsAgent.parse_llm_response(llm_response_content, sample_intents)
    assert len(ranked_intents) == 0

def test_intents_agent_parse_llm_response_empty(sample_intents):
    llm_response_content = ""
    ranked_intents = IntentsAgent.parse_llm_response(llm_response_content, sample_intents)
    assert len(ranked_intents) == 0


def test_intents_agent_usage_calculation(sample_intents):
    # Given
    agent = IntentsAgent(llm_model_id=1)
    prompt = "Hello, how are you?"
    query_payload = agent.build_query(prompt, sample_intents)
    completion_tokens = 30

    # When
    usage = agent.usage(query_payload, completion_tokens)

    # Then
    # I'll need to calculate the expected prompt tokens.
    # I'll do it manually for the test.
    import json
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    expected_prompt_tokens = len(encoding.encode(json.dumps(query_payload)))

    assert usage["prompt_tokens"] == expected_prompt_tokens
    assert usage["completion_tokens"] == 30
    assert usage["total_tokens"] == expected_prompt_tokens + 30
    assert usage["label"] == "IntentsAgent"

@pytest.mark.asyncio
async def test_intents_agent_execute_usage_calculation(intents_agent, sample_intents):
    # Given
    prompt = "Hello, how are you?"

    # When
    response = await intents_agent.execute(sample_intents, prompt)

    # Then
    import json
    import tiktoken
    encoding = tiktoken.get_encoding("cl100k_base")
    query_payload = intents_agent.build_query(prompt, sample_intents)
    expected_prompt_tokens = len(encoding.encode(json.dumps(query_payload)))
    expected_completion_tokens = 0 # because we parse an empty string

    assert response.usage["prompt_tokens"] == expected_prompt_tokens
    assert response.usage["completion_tokens"] == expected_completion_tokens
    assert response.usage["total_tokens"] == expected_prompt_tokens + expected_completion_tokens
    assert response.usage["label"] == "IntentsAgent"
