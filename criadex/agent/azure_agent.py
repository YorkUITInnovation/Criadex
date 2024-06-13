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
import traceback
from abc import abstractmethod
from typing import List, Optional, Union

import openai
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.prompts import ChatPromptTemplate
from openai.types import CompletionUsage
from pydantic import BaseModel

from criadex.agent.base_agent import BaseAgentResponse, BaseAgent
from criadex.criadex import Criadex
from criadex.index.base_api import CriadexIndexAPI
from criadex.index.llama_objects.models import CriaAzureOpenAI, ContentFilterError


class LLMAgentModelConfig(BaseModel):
    """
    Model configuration for an LLM agent

    """

    max_reply_tokens: Optional[int] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None


class LLMAgentResponse(BaseAgentResponse):
    """
    LLMAgentResponse

    """

    usage: List[CompletionUsage]


class LLMAgent(BaseAgent):
    """
    A base LLM agent

    """

    def __init__(
            self,
            criadex: Criadex,
            llm_model_id: int,
            model_config: Optional[LLMAgentModelConfig]
    ):
        """
        Initialize the LLM agent

        :param criadex: Instance of the Criadex API
        :param llm_model_id: The LLM model ID to use
        :param model_config: The LLM model configuration

        """

        self._criadex: Criadex = criadex
        self._llm_model_id: int = llm_model_id
        self._llm: Optional[CriaAzureOpenAI] = None
        self._model_config_dict: dict = self.parse_model_config(model_config)

    @classmethod
    def parse_model_config(cls, model_config: Optional[LLMAgentModelConfig]) -> dict:
        """
        Parse a model config for the agent

        :param model_config: The model config to parse
        :return: The parsed config

        """

        if not model_config:
            return dict()

        include_set: dict = {key: value for key, value in model_config.dict().items() if value is not None}

        if "max_reply_tokens" in include_set:
            del include_set["max_reply_tokens"]
            include_set["max_tokens"] = model_config.max_reply_tokens

        return include_set

    async def load_llm(self) -> CriaAzureOpenAI:
        """
        Load the LLM model for the agent

        :return: The LLM model

        """

        if self._llm is None:
            self._llm: CriaAzureOpenAI = CriadexIndexAPI.build_llm_model(
                azure_model=await self._criadex.about_azure_model(
                    model_id=self._llm_model_id
                ),
                **self._model_config_dict
            )

        return self._llm

    async def query_model(self, history: List[ChatMessage]) -> ChatResponse:
        """
        Query an Azure model within the agent

        :param history: The specially-built chat history
        :return: The response

        :raises ModelNotFoundError: If the model is not found
        :raises ValueError: If the model is not an LLM model
        """

        # If it doesn't exist, we build it
        await self.load_llm()

        try:
            return await self._llm.apredict(
                prompt=ChatPromptTemplate(message_templates=history),
                return_as_str=False
            )
        except openai.BadRequestError as ex:
            if ex.code == 'content_filter':
                logging.error(ex.message + "\n" + json.dumps([h.dict() for h in history], indent=4))
                raise ContentFilterError("Hit an OpenAI filter") from ex
            raise ex

    def usage(self, prompt: Union[str, List[ChatMessage]]) -> List[CompletionUsage]:
        """
        Calculate the usage of the LLM model

        :param prompt: The prompt to calculate the usage for
        :return: The usage

        """

        if isinstance(prompt[0], ChatMessage):
            prompt: str = self._llm.get_prompt(prompt)

        return self._llm.pop_hash(prompt)

    @abstractmethod
    async def execute(self, **kwargs: dict) -> LLMAgentResponse:
        """
        Execute the agent. This is overridable.

        :param kwargs: Overridable kwargs
        :return: Agent's response

        """

        raise NotImplementedError
