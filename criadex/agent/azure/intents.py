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

from llama_index.core.base.llms.types import ChatMessage, MessageRole, ChatResponse
from llama_index.core.prompts import PromptTemplate
from pydantic import BaseModel

from ..azure_agent import LLMAgentResponse, LLMAgent


class Intent(BaseModel):
    """
    An intent

    """

    name: str
    description: str


class RankedIntent(Intent):
    """
    A ranked intent

    """

    score: float


class IntentsAgentResponse(LLMAgentResponse):
    """
    Response from the IntentsAgent

    """

    ranked_intents: List[RankedIntent]


class IntentsAgent(LLMAgent):
    """Rank relevant categories based on a prompt & category list"""

    SYSTEM_MESSAGE: str = (

        "[INSTRUCTIONS]\n"
        "A list of categories is shown below. "
        "Respond with the number of each category, in order of its relevance to the question, "
        "as well as the relevance score, a number from 1-10 based on how "
        "relevant you think the category is to the question.\n"

        "Do not include any categories that are not relevant to the question.\n\n"

        "Here's an example prompt:\n"
        "Category 1: \n<name 1>\n<description of category 1>\n\n"
        "Category 2: \n<name 2>\n<description of category 2>\n\n"
        "...\n\n"
        "Category 10: \n<name 10>\n<description of category 2>\n\n"
        "Question: <question>\n"
        "Your Answer:\n"
        "Category: 9, Relevance: 7\n"
        "Category: 3, Relevance: 4\n\n"
        "Let's try this now:\n\n"
    )

    USER_TEMPLATE: PromptTemplate = PromptTemplate(
        "{categories}\n\n"
        "Question: {question}\n"
        "Your Answer:"
    )

    USER_CATEGORY: PromptTemplate = PromptTemplate(
        "Category {num}:\n{name}\n{description})"
    )

    def build_llm_query(
            self,
            prompt: str,
            intents: List[Intent]
    ) -> List[ChatMessage]:
        """
        Build an LLM query for ranking the intents

        :param prompt: The prompt to rank the intents based on
        :param intents: The list of intents to rank
        :return: The query

        """

        # Get the category list
        categories: List[str] = [
            self.USER_CATEGORY.format(
                num=idx,
                name=intent.name,
                description=intent.description
            ) for idx, intent in enumerate(intents)
        ]

        return [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=self.SYSTEM_MESSAGE
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=self.USER_TEMPLATE.format(
                    categories=categories,
                    question=prompt
                )
            )
        ]

    @classmethod
    def _parse_llm_response(
            cls,
            llm_response: ChatResponse,
            intents: List[Intent]
    ) -> List[RankedIntent]:
        """
        Given a response from the LLM (based on build_query_chat), extract the correct rankings from the string

        :param intents: The list of intents
        :param llm_response: The response
        :return: The intents, ranked in order of relevance to the query

        """

        ranked_categories: List[str] = llm_response.message.content.split("\n")
        ranked_intents: List[RankedIntent] = []

        for category in ranked_categories:

            if "category" not in category.lower():
                raise ValueError("Invalid LLM Response")

            # Horrible bit of string parsing that should likely be replaced with regex
            cat_idx: int = int(category[category.find(" ") + 1: category.find(", ")]) - 1
            cat_rank: int = int(category[category.rfind(": ") + 2:])

            ranked_intents.append(
                RankedIntent(
                    score=float(cat_rank / 10),
                    **intents[cat_idx].dict()
                )
            )

        return ranked_intents

    async def execute(
            self,
            intents: List[Intent],
            prompt: str,
    ) -> IntentsAgentResponse:
        """
        Rank intents executor

        :param intents: The list of intents to rank
        :param prompt: The prompt to rank the intents based on
        :return: The ranked intents

        """

        query: List[ChatMessage] = self.build_llm_query(
            prompt=prompt,
            intents=intents
        )

        # Ask the LLM for a reply
        response: ChatResponse = await self.query_model(
            history=query
        )

        # Wrap it in a bow
        return IntentsAgentResponse(
            ranked_intents=self._parse_llm_response(response, intents),
            usage=self.usage(query, usage_label="IntentsAgent")
        )
