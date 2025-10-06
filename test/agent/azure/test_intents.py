import pytest
from unittest.mock import AsyncMock, MagicMock
from criadex.agent.azure.intents import Intent, RankedIntent, IntentsAgentResponse, IntentsAgent
from criadex.index.ragflow_objects.intents import RagflowIntentsAgent, RagflowIntentsAgentResponse

@pytest.fixture
def intents_agent():
    agent = IntentsAgent(llm_model_id=1)
    # Mock the query_model method of the RagflowIntentsAgent base class
    agent.query_model = AsyncMock()
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
    llm_response_content = "1. category: Greeting, score: 9\n2. category: Question, score: 7"

    intents_agent.query_model.return_value = MagicMock(
        message=MagicMock(content=llm_response_content)
    )

    response = await intents_agent.execute(sample_intents, prompt)

    # Assertions
    intents_agent.query_model.assert_called_once()
    assert isinstance(response, IntentsAgentResponse)
    assert len(response.ranked_intents) == 2
    assert response.ranked_intents[0].name == "Greeting"
    assert response.ranked_intents[0].score == 0.9
    assert response.ranked_intents[1].name == "Question"
    assert response.ranked_intents[1].score == 0.7
    assert response.message == "Successfully ranked intents"
    assert "prompt_tokens" in response.usage
    assert "completion_tokens" in response.usage
    assert "total_tokens" in response.usage
    assert "label" in response.usage

@pytest.mark.asyncio
async def test_intents_agent_execute_empty_llm_response(intents_agent, sample_intents):
    prompt = "Empty response test"
    llm_response_content = ""

    intents_agent.query_model.return_value = MagicMock(
        message=MagicMock(content=llm_response_content)
    )

    response = await intents_agent.execute(sample_intents, prompt)

    intents_agent.query_model.assert_called_once()
    assert isinstance(response, IntentsAgentResponse)
    assert len(response.ranked_intents) == 0
    assert response.message == "Successfully ranked intents"

@pytest.mark.asyncio
async def test_intents_agent_execute_malformed_llm_response(intents_agent, sample_intents):
    prompt = "Malformed response test"
    llm_response_content = "This is not a valid ranking line."

    intents_agent.query_model.return_value = MagicMock(
        message=MagicMock(content=llm_response_content)
    )

    response = await intents_agent.execute(sample_intents, prompt)

    intents_agent.query_model.assert_called_once()
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
