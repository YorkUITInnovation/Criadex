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

import textwrap
from typing import List, Optional

from llama_index.core import PromptTemplate
from llama_index.core.base.llms.types import ChatResponse, ChatMessage
from pydantic import BaseModel

from ..azure_agent import LLMAgent, LLMAgentResponse


class TransformAgentResponse(LLMAgentResponse):
    new_prompt: Optional[str] = None


class TransformAgentConfig(BaseModel):
    prompt: str
    history: List[ChatMessage]


CHAT_MESSAGE_PROMPT: PromptTemplate = PromptTemplate(
    "{role}: {content}"
)

USER_MESSAGE_PROMPT: PromptTemplate = PromptTemplate(
    textwrap.dedent("""
        {chat_history}

        Prompt:
        {prompt}
        
        Your Reply:\n
    """)
)

QUERY_AGENT_PROMPT: PromptTemplate = PromptTemplate(
    textwrap.dedent("""
    [INSTRUCTIONS]
    You are a tool to transform user prompts.
    A conversation history is provided below, along with a user's new prompt. Using the history, reply with a new prompt
    from the perspective of THE USER and include any contextual information from the history IF it is needed for the prompt 
    to make sense on its own. Do NOT add any extra information. Most recent messages will have the most relevant context.
    
    Here's an example:
    
    user: I love to cook.
    assistant: Amazing!
    
    Query: 
    What should I?
    
    Your Reply:
    What should I cook?

    Let's try this now:
    """)
)


class TransformAgent(LLMAgent):

    async def execute(
            self,
            config: TransformAgentConfig
    ) -> TransformAgentResponse:
        agent_prompt: str = QUERY_AGENT_PROMPT.format()
        user_prompt: str = USER_MESSAGE_PROMPT.format(
            chat_history=self.create_user_messages(config.history),
            prompt=config.prompt
        )

        history: List[ChatMessage] = [
            ChatMessage(
                role="system",
                content=agent_prompt
            ),
            ChatMessage(
                role="user",
                content=user_prompt
            )
        ]

        response: ChatResponse = await self.query_model(
            history=history
        )

        return TransformAgentResponse(
            new_prompt=response.message.content,
            usage=self.usage(history, usage_label="TransformAgent"),
            message="Successfully queried the model!"
        )

    @classmethod
    def create_user_messages(cls, history: List[ChatMessage]) -> str:
        message_str: str = ""

        for message in history:

            # only include the conversation
            if message.role not in ["assistant", "user"]:
                continue

            message_str += CHAT_MESSAGE_PROMPT.format(
                role=message.role,
                content=message.content
            )

        return message_str
