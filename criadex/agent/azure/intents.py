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
from typing import List, Optional, Any

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
    def __init__(self, ranked_intents: List[RankedIntent], usage: dict, message: str = "Successfully ranked intents", model_id: int = 0):
        super().__init__(message=message, model_id=model_id) # Only pass message and model_id to super
        self.ranked_intents = ranked_intents # Store ranked_intents directly
        self.usage = usage


class IntentsAgent(RagflowIntentsAgent):
    """
    Ragflow-based IntentsAgent with legacy feature parity: ranking, parsing, error handling.
    """
    def __init__(self, llm_model_id: int):
        super().__init__()
        self.llm_model_id = llm_model_id

    def usage(self, payload: dict, usage_label: str = "IntentsAgent") -> dict:
        """
        Calculate token usage based on the payload.
        For now, this is a placeholder.
        """
        total_tokens = sum(len(str(value).split()) for value in payload.values())
        return {
            "prompt_tokens": total_tokens,
            "completion_tokens": 0,  # Placeholder
            "total_tokens": total_tokens,
            "label": usage_label
        }

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
                # Extract the number at the beginning of the line
                parts = line.split('.')
                if len(parts) > 1 and parts[0].strip().isdigit():
                    cat_num_str = parts[0].strip()
                    cat_idx = int(cat_num_str) - 1
                else:
                    raise ValueError("Could not extract category index")

                # Extract the score
                score_start_idx = line.rfind("score:") + len("score:")
                cat_rank_str = line[score_start_idx:].strip()
                cat_rank = int(cat_rank_str)

                # Check if cat_idx is valid
                if not (0 <= cat_idx < len(intents)):
                    raise IndexError(f"Category index {cat_idx} is out of bounds for intents list of length {len(intents)}")

                ranked_intents.append(
                    RankedIntent(
                        score=float(cat_rank) / 10.0,
                        **intents[cat_idx].model_dump()
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
        return IntentsAgentResponse(
            ranked_intents=ranked_intents,
            usage=self.usage(query_payload, usage_label="IntentsAgent"),
            model_id=self.llm_model_id
        )