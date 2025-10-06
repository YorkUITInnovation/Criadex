import pytest
from unittest.mock import AsyncMock, MagicMock
from criadex.agent.azure.chat import ChatAgent, ChatAgentResponse
from criadex.index.ragflow_objects.chat import RagflowChatAgent, RagflowChatAgentResponse

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
    chat_agent.usage.assert_called_once_with(history, usage_label="ChatAgent")

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
    chat_agent.usage.assert_called_once_with(history, usage_label="ChatAgent")

    assert isinstance(response, ChatAgentResponse)
    assert response.chat_response == {"content": "Empty history response"}
    assert response.message == "Successfully queried the model!"
