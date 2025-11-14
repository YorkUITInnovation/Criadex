import pytest
from unittest.mock import AsyncMock, MagicMock
from criadex.agent.azure.chat import ChatAgent, ChatAgentResponse

@pytest.fixture
def chat_agent():
    agent = ChatAgent(llm_model_id=1)
    # Mock the query_model method of the RagflowChatAgent base class
    agent.query_model = AsyncMock(return_value=MagicMock(message=MagicMock(model_dump=lambda: {"content": "Mocked response"})))
    # Mock the usage method of the ChatAgent instance
    agent.usage = MagicMock(return_value={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30})
    return agent

@pytest.mark.asyncio
async def test_chat_agent_execute_positive(chat_agent):
    # Sample history data
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]

    # Execute the chat agent
    response = await chat_agent.execute(history)

    # Assertions
    chat_agent.query_model.assert_called_once_with(history)
    chat_agent.usage.assert_called_once_with(history, 3, usage_label="ChatAgent")

    assert isinstance(response, ChatAgentResponse)
    assert response.chat_response == {"content": "Mocked response"}
    assert response.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    assert response.message == "Successfully queried the model!"

@pytest.mark.asyncio
async def test_chat_agent_execute_with_non_pydantic_message(chat_agent):
    history = [
        {"role": "user", "content": "Test"}
    ]

    # Mock the query_model response with a non-Pydantic message
    chat_agent.query_model.return_value = MagicMock(
        message="Simple string response"
    )

    response = await chat_agent.execute(history)

    assert isinstance(response, ChatAgentResponse)
    assert response.chat_response == "Simple string response"
    assert response.message == "Successfully queried the model!"

@pytest.mark.asyncio
async def test_chat_agent_execute_empty_history(chat_agent):
    history = []

    chat_agent.query_model.return_value = MagicMock(
        message=MagicMock(model_dump=lambda: {"content": "Empty history response"})
    )

    response = await chat_agent.execute(history)

    chat_agent.query_model.assert_called_once_with(history)
    chat_agent.usage.assert_called_once_with(history, 3, usage_label="ChatAgent")

    assert isinstance(response, ChatAgentResponse)
    assert response.chat_response == {"content": "Empty history response"}
    assert response.message == "Successfully queried the model!"


def test_chat_agent_usage_calculation():
    # Given
    agent = ChatAgent(llm_model_id=1)
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    completion_tokens = 20

    # When
    usage = agent.usage(history, completion_tokens)

    # Then
    # "Hello" is 1 token. "Hi there!" is 3 tokens.
    assert usage["prompt_tokens"] == 4
    assert usage["completion_tokens"] == 20
    assert usage["total_tokens"] == 24
    assert usage["label"] == "ChatAgent"

@pytest.mark.asyncio
async def test_chat_agent_execute_usage_calculation():
    # Given
    agent = ChatAgent(llm_model_id=1)
    agent.query_model = AsyncMock(return_value=MagicMock(message="This is a response.")) # 5 tokens
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]

    # When
    response = await agent.execute(history)

    # Then
    # "Hello" is 1 token. "Hi there!" is 3 tokens.
    assert response.usage["prompt_tokens"] == 4
    # "This is a response." is 5 tokens
    assert response.usage["completion_tokens"] == 5
    assert response.usage["total_tokens"] == 9
    assert response.usage["label"] == "ChatAgent"
