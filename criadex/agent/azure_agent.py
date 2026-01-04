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

import json
import logging
from abc import abstractmethod
from typing import List, Optional, Union

from criadex.index.ragflow_objects.schemas import RagflowChatMessage, RagflowChatResponse
from criadex.index.ragflow_objects.llm import RagflowLLMAgent, RagflowLLMAgentResponse, RagflowLLM
from pydantic import BaseModel

from criadex.agent.base_agent import BaseAgentResponse, BaseAgent
from criadex.criadex import Criadex
from criadex.index.base_api import CriadexIndexAPI


class LLMAgentModelConfig(BaseModel):
    """
    Model configuration for an LLM agent

    """

    max_reply_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class LLMAgentResponse(RagflowLLMAgentResponse):
    pass


class LLMAgent(RagflowLLMAgent):
    """
    Ragflow-based LLMAgent with legacy feature parity: model config parsing, async LLM loading, usage calculation, error handling.
    """

    def __init__(self, criadex: Criadex, llm_model_id: int, model_config: Optional[LLMAgentModelConfig]):
        self._criadex: Criadex = criadex
        self._llm_model_id: int = llm_model_id
        self._llm: Optional[RagflowLLM] = None
        self._model_config_dict: dict = self.parse_model_config(model_config)

    @classmethod
    def parse_model_config(cls, model_config: Optional[LLMAgentModelConfig]) -> dict:
        if not model_config:
            return dict()
        include_set: dict = {key: value for key, value in model_config.dict().items() if value is not None}
        if "max_reply_tokens" in include_set:
            del include_set["max_reply_tokens"]
            include_set["max_tokens"] = model_config.max_reply_tokens
        return include_set

    async def load_llm(self) -> RagflowLLM:
        if self._llm is None:
            # Adapted for Ragflow: build LLM model
            self._llm = await self._criadex.get_ragflow_llm(self._llm_model_id, **self._model_config_dict)
        return self._llm

    async def query_model(self, history: List[RagflowChatMessage]) -> RagflowChatResponse:
        await self.load_llm()
        try:
            return await self._llm.apredict(history)
        except Exception as ex:
            logging.error(f"Error querying Ragflow model: {ex}")
            raise ex

    def usage(self, prompt: Union[str, List[RagflowChatMessage]], usage_label: str) -> List[dict]:
        # Usage calculation (adapted from legacy)
        if isinstance(prompt, list) and prompt and isinstance(prompt[0], RagflowChatMessage):
            prompt_str = " ".join([msg.content for msg in prompt])
        else:
            prompt_str = str(prompt)
        return [{"usage_label": usage_label, "prompt": prompt_str}]