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

from typing import List, Optional

from criadex.index.ragflow_objects.chat import RagflowChatAgent, RagflowChatAgentResponse


## ExtendedChatResponse is not needed with RagflowChatAgentResponse


class ChatAgentResponse(RagflowChatAgentResponse):
    pass


class ChatAgent(RagflowChatAgent):
    """
    Ragflow-based ChatAgent with legacy feature parity: response normalization, usage calculation, error handling.
    """

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
            message="Successfully queried the model!"
        )
