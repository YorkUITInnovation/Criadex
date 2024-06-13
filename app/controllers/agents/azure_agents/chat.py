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

from typing import Optional, Union, List

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from llama_index.core.base.llms.types import ChatMessage
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, \
    NOT_FOUND, INVALID_MODEL, INVALID_REQUEST, ERROR, OPENAI_FILTER
from app.core.config import QUERY_MODEL_RATE_LIMIT_HOUR, QUERY_MODEL_RATE_LIMIT_DAY, QUERY_MODEL_RATE_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import model_query_limiter
from criadex.agent.azure.chat import ChatAgentResponse, ChatAgent
from criadex.agent.azure_agent import LLMAgentModelConfig
from criadex.index.llama_objects.models import EmptyPromptError, ContentFilterError
from criadex.schemas import ModelNotFoundError

view = APIRouter()


class AgentChatResponse(APIResponse):
    agent_response: Optional[ChatAgentResponse] = None
    code: Union[SUCCESS, NOT_FOUND, INVALID_MODEL, INVALID_REQUEST, OPENAI_FILTER, ERROR]


class ChatAgentConfig(LLMAgentModelConfig):
    history: List[ChatMessage]


@cbv(view)
class ChatAgentRoute(CriaRoute):
    ResponseModel = AgentChatResponse

    @view.post(
        path="/models/azure/{model_id}/agents/chat",
        name="Chat with an Azure Model",
        summary="Chat with an Azure Model",
        description="Chat with an Azure Model <u>IF THE MODEL IS USED IN AN INDEX YOUR API KEY HAS ACCESS TO</u>",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        ModelNotFoundError,
        ResponseModel(
            code="NOT_FOUND",
            status=404,
            message="The requested model ID does not exist!",
        )
    )
    @exception_response(
        EmptyPromptError,
        ResponseModel(
            code="INVALID_REQUEST",
            status=400,
            message="The prompt supplied was empty."
        )
    )
    @exception_response(
        ContentFilterError,
        ResponseModel(
            code="OPENAI_FILTER",
            status=400,
            message="Hit an OpenAI content filter."
        )
    )
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_DAY)
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_HOUR)
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_MINUTE)
    async def execute(self, request: Request, model_id: int, config: ChatAgentConfig) -> ResponseModel:
        agent: ChatAgent = ChatAgent(
            criadex=request.app.criadex,
            llm_model_id=model_id,
            model_config=LLMAgentModelConfig(**config.dict())
        )

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully queried the Azure model!",
            agent_response=await agent.execute(
                history=config.history
            )
        )


__all__ = ["view"]
