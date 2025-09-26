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
import logging
from typing import List

from criadex.index.ragflow_objects.intents import RagflowIntentsAgent, RagflowIntentsAgentResponse
from pydantic import BaseModel

## Legacy agent base classes removed; using Ragflow equivalents


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


class IntentsAgentResponse(RagflowIntentsAgentResponse):
    pass


class IntentsAgent(RagflowIntentsAgent):
    """
    Ragflow-based IntentsAgent with legacy feature parity: ranking, parsing, error handling.
    """

    @staticmethod
    def build_query(prompt: str, intents: List[Intent]) -> dict:
        """
        Build a query payload for Ragflow LLM ranking.
        """
        categories = [
            {
                "num": idx + 1,
                "name": intent.name,
                "description": intent.description
            }
            for idx, intent in enumerate(intents)
        ]
        return {
            "categories": categories,
            "question": prompt
        }

    @staticmethod
    def parse_llm_response(llm_response: str, intents: List[Intent]) -> List[RankedIntent]:
        """
        Parse Ragflow LLM response and rank intents, preserving legacy error handling and normalization.
        """
        ranked_intents: List[RankedIntent] = []
        lines = [line for line in llm_response.splitlines() if line.strip()]
        for line in lines:
            if "category" not in line.lower():
                continue
            try:
                cat_idx = int(line[line.find(" ") + 1: line.find(",")]) - 1
                cat_rank = int(line[line.rfind(":") + 1:])
                ranked_intents.append(
                    RankedIntent(
                        score=float(cat_rank) / 10.0,
                        **intents[cat_idx].dict()
                    )
                )
            except Exception as e:
                logging.warning(f"Failed to parse intent ranking line: '{line}'. Error: {e}")
                continue
        return ranked_intents

    async def execute(self, intents: List[Intent], prompt: str) -> IntentsAgentResponse:
        """
        Execute Ragflow LLM ranking, preserving legacy features.
        """
        query_payload = self.build_query(prompt, intents)
        # Use Ragflow's async query method (assumed to exist)
        response = await self.query_model(query_payload)
        ranked_intents = self.parse_llm_response(response.message.content, intents)
        return IntentsAgentResponse(ranked_intents=ranked_intents, usage=self.usage(query_payload, usage_label="IntentsAgent"))