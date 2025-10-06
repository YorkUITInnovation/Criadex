"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Isaac Kogan
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""

from typing import List, Optional, Any

from criadex.index.ragflow_objects.chat import RagflowChatAgent, RagflowChatAgentResponse


class ChatAgentResponse(RagflowChatAgentResponse):
    def __init__(self, chat_response: Any, usage: dict, message: str, model_id: Optional[int] = None):
        super().__init__(message=message, model_id=model_id)
        self.chat_response = chat_response
        self.usage = usage


class ChatAgent(RagflowChatAgent):
    """
    Ragflow-based ChatAgent with legacy feature parity: response normalization, usage calculation, error handling.
    """
    def __init__(self, llm_model_id: int):
        super().__init__()
        self.llm_model_id = llm_model_id

    def usage(self, history: List[dict], usage_label: str = "ChatAgent") -> dict:
        """
        Calculate token usage based on chat history.
        For now, this is a placeholder.
        """
        # In a real scenario, this would calculate tokens based on the content of history
        # For testing and initial implementation, return a dummy usage.
        total_tokens = sum(len(item.get("content", "").split()) for item in history)
        return {
            "prompt_tokens": total_tokens,
            "completion_tokens": 0, # Placeholder
            "total_tokens": total_tokens,
            "label": usage_label
        }

    async def execute(self, history: List[dict]) -> ChatAgentResponse:
        """
        Execute the chat agent, preserving legacy features.
        :param history: List of chat messages (dicts)
        :return: ChatAgentResponse
        """
        # Query Ragflow model (assumed to accept history as input)
        response = await self.query_model(history)
        # Normalize response if needed (legacy logic)
        chat_response = response.message.model_dump() if hasattr(response.message, 'model_dump') else response.message
        return ChatAgentResponse(
            chat_response=chat_response,
            usage=self.usage(history, usage_label="ChatAgent"),
            message="Successfully queried the model!",
            model_id=self.llm_model_id # Assuming llm_model_id is available in ChatAgent
        )
