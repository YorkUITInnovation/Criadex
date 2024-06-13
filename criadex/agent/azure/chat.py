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

from typing import List

from llama_index.core.base.llms.types import ChatResponse, ChatMessage

from ..azure_agent import LLMAgent, LLMAgentResponse


class ChatAgentResponse(LLMAgentResponse):
    """
    Response from the ChatAgent

    """

    chat_response: ChatResponse


class ChatAgent(LLMAgent):
    """
    Agent to query a model's chat endpoint

    """

    async def execute(
            self,
            history: List[ChatMessage]
    ) -> ChatAgentResponse:
        """
        Execute the agent

        :param history: The chat history to use in the query
        :return: The response from the agent

        """

        response: ChatResponse = await self.query_model(
            history=history
        )

        return ChatAgentResponse(
            chat_response=response,
            usage=self.usage(history),
            message="Successfully queried the model!"
        )
