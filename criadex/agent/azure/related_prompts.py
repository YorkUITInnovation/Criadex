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

from criadex.index.ragflow_objects.related_prompts import RagflowRelatedPromptsAgent, RagflowRelatedPromptsAgentResponse
from criadex.index.ragflow_objects.schemas import RagflowChatMessage, RagflowChatResponse
from criadex.index.index_api.question.index_objects import RelatedPrompt
## PromptTemplate import removed; use plain string formatting


class RelatedPromptsGenerationAgentResponse(RagflowRelatedPromptsAgentResponse):
    """
    Response from the IntentsAgent
    """
    related_prompts: List[RelatedPrompt]


class RelatedPromptsGenerationAgent(RagflowRelatedPromptsAgent):
    """Automatically generate related prompts"""

    DIVIDER_TEXT: str = "<>"

    SYSTEM_MESSAGE: str = (

        "[INSTRUCTIONS]\n"
        "You are an LLM agent. Your task is to generate related questions based on a given question & answer. "
        "Create 3 related but DIFFERENT questions a user might want to ask based on the prompt & answer given. For each question, include a label. "
        f"Each question-label pair should be separated by the following divider tag for parsing: {DIVIDER_TEXT}. "
        f"Each question-label pair should be separated by a newline character."

        "Here's an example response:\n"

        f"Applying For OSAP{DIVIDER_TEXT}How do I apply for OSAP?\n"
        f"Dropping Out{DIVIDER_TEXT}How do I drop out of university?\n"
        f"Tuition Waiver{DIVIDER_TEXT}How do I get a tuition waiver?\n\n"

        "Let's try this now:\n\n"
    )

    USER_TEMPLATE: str = (
        "[PROMPT]\n{llm_prompt}\n\n"
        "[LLM-Generated Answer]\n{llm_reply}\n\n"
    )

    def build_llm_query(self, llm_prompt: str, llm_reply: str) -> List[RagflowChatMessage]:
        return [
            RagflowChatMessage(
                role="system",
                content=self.SYSTEM_MESSAGE
            ),
            RagflowChatMessage(
                role="user",
                content=self.USER_TEMPLATE.format(
                    llm_prompt=llm_prompt,
                    llm_reply=llm_reply,
                )
            )
        ]

    @classmethod
    def _parse_llm_response(cls, llm_response: RagflowChatResponse) -> List[RelatedPrompt]:
        related_questions: List[str] = llm_response.message.content.split("\n")
        related_prompts: List[RelatedPrompt] = []
        for related_question in related_questions:
            if not related_question:
                continue
            label, prompt = related_question.split(cls.DIVIDER_TEXT)
            related_prompts.append(
                RelatedPrompt(
                    label=label,
                    prompt=prompt,
                    llm_generated=True
                )
            )
        return related_prompts

    async def execute(
            self,
            llm_prompt: str,
            llm_reply: str
    ) -> RelatedPromptsGenerationAgentResponse:
        """
        Rank intents executor
        """

        history: List[RagflowChatMessage] = self.build_llm_query(
            llm_prompt=llm_prompt,
            llm_reply=llm_reply
        )

        # Ask the LLM for a reply
        response: RagflowChatResponse = await self.query_model(
            history=history
        )

        # Wrap it in a bow
        return RelatedPromptsGenerationAgentResponse(
            related_prompts=self._parse_llm_response(response),
            usage=self.usage(history, usage_label="RelatedPromptsAgent")
        )