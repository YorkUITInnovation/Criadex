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


import tiktoken
from typing import List, Optional, Any
from criadex.index.ragflow_objects.chat import RagflowChatAgent
from pydantic import BaseModel

class ChatAgentResponse(BaseModel):
    chat_response: Any
    usage: dict
    message: str
    model_id: Optional[str] = None



class ChatAgent(RagflowChatAgent):
    """
    Ragflow-based ChatAgent with legacy feature parity: response normalization, usage calculation, error handling.
    """
    def __init__(self, llm_model_id: str):
        super().__init__()
        self.llm_model_id = llm_model_id

    def usage(self, history: List[dict], completion_tokens: int, usage_label: str = "ChatAgent") -> dict:
        """
        Calculate token usage based on chat history.
        For now, this is a placeholder.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        prompt_tokens = 0
        for message in history:
            if 'content' in message and message['content']:
                prompt_tokens += len(encoding.encode(message['content']))

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "label": usage_label
        }

    async def query_model(self, history: List[dict], chat_id: str, api_key: str):
        class MockResponse:
            def __init__(self, data):
                self.message = data

        response_dict = await self.chat(chat_id, history, api_key)
        return MockResponse(response_dict["chat_response"])

    async def execute(self, history: List[dict], chat_id: str, api_key: str) -> ChatAgentResponse:
        """
        Execute the chat agent, preserving legacy features.
        :param history: List of chat messages (dicts)
        :return: ChatAgentResponse
        """
        # Query Ragflow model (assumed to accept history as input)
        response = await self.query_model(history, chat_id, api_key)
        # Normalize response if needed (legacy logic)
        chat_response = response.message.model_dump() if hasattr(response.message, 'model_dump') else response.message
        
        encoding = tiktoken.get_encoding("cl100k_base")

        content_to_encode = ""
        if isinstance(chat_response, dict):
            if "content" in chat_response:
                content_to_encode = chat_response["content"]
            elif "message" in chat_response and "blocks" in chat_response["message"] and chat_response["message"]["blocks"]:
                content_to_encode = chat_response["message"]["blocks"][0].get("text", "")
        else:
            content_to_encode = str(chat_response)

        completion_tokens = len(encoding.encode(content_to_encode))

        return ChatAgentResponse(
            chat_response=chat_response,
            usage=self.usage(history, completion_tokens, usage_label="ChatAgent"),
            message="Successfully queried the model!",
            model_id=str(self.llm_model_id)
        )
