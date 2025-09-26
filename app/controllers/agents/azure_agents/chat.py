class EmptyPromptError(Exception):
    pass

class ContentFilterError(Exception):
    pass
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
from criadex.index.ragflow_objects.schemas import RagflowChatMessage
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, \
    NOT_FOUND, INVALID_MODEL, INVALID_REQUEST, ERROR, OPENAI_FILTER
from app.core.config import QUERY_MODEL_RATE_LIMIT_HOUR, QUERY_MODEL_RATE_LIMIT_DAY, QUERY_MODEL_RATE_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import model_query_limiter
from criadex.index.ragflow_objects.chat import RagflowChatAgentResponse, RagflowChatAgent
from criadex.index.ragflow_objects.llm import RagflowLLMAgentModelConfig
from criadex.schemas import ModelNotFoundError

view = APIRouter()



# Use RagflowChatAgentResponse for agent_response, keep all error/status codes
class AgentChatResponse(APIResponse):
    agent_response: Optional[RagflowChatAgentResponse] = None
    code: str



# Use RagflowLLMAgentModelConfig and RagflowChatMessage for config/history
class ChatAgentConfig(RagflowLLMAgentModelConfig):
    history: List[RagflowChatMessage]



@cbv(view)
class ChatAgentRoute(CriaRoute):
    ResponseModel = AgentChatResponse

    @view.post(
        path="/models/ragflow/{model_id}/agents/chat",
        name="Chat with a Ragflow Model",
        summary="Chat with a Ragflow Model",
        description="Chat with a Ragflow Model <u>IF THE MODEL IS USED IN AN INDEX YOUR API KEY HAS ACCESS TO</u>",
    )
    @catch_exceptions(ResponseModel)
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
    async def execute(self, request: Request, model_id: int, config: ChatAgentConfig) -> AgentChatResponse:
        agent = RagflowChatAgent(
            criadex=request.app.criadex,
            llm_model_id=model_id,
            model_config=config
        )
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully queried the Ragflow model!",
            agent_response=await agent.execute(
                history=config.history
            )
        )


__all__ = ["view"]
