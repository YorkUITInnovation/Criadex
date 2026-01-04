import pytest
from unittest.mock import AsyncMock, patch
from criadex.bot.bot import Bot

@pytest.mark.asyncio
async def test_bot_chat():
    # Given
    mock_vector_store = AsyncMock()
    mock_embedder = AsyncMock()
    bot = Bot(vector_store=mock_vector_store, embedder=mock_embedder)

    message = "Hello, bot!"
    llm_model_id = 1

    with patch('criadex.bot.bot.ChatAgent') as mock_chat_agent:
        mock_agent_instance = mock_chat_agent.return_value
        mock_agent_instance.execute = AsyncMock(return_value="mocked_response")

        # When
        response = await bot.chat(message, llm_model_id)

        # Then
        mock_chat_agent.assert_called_once_with(llm_model_id=llm_model_id)
        mock_agent_instance.execute.assert_called_once()
        
        # Check the history that was passed to execute
        history_arg = mock_agent_instance.execute.call_args[1]['history']
        assert history_arg == [{"role": "user", "content": message}]
        
        assert response == "mocked_response"
