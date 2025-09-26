# Local error definitions to replace legacy imports
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

from typing import Optional, Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, \
    NOT_FOUND, INVALID_MODEL, INVALID_REQUEST, ERROR, OPENAI_FILTER
from app.core.config import QUERY_MODEL_RATE_LIMIT_HOUR, QUERY_MODEL_RATE_LIMIT_DAY, QUERY_MODEL_RATE_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import model_query_limiter
from criadex.index.ragflow_objects.transform import RagflowTransformAgentResponse, RagflowTransformAgentConfig, RagflowTransformAgent
from criadex.index.ragflow_objects.llm import RagflowLLMAgentModelConfig
# Remove legacy import. If needed, define EmptyPromptError and ContentFilterError locally or import from new location.
from criadex.schemas import ModelNotFoundError

view = APIRouter()



# Use RagflowTransformAgentResponse for agent_response, keep all error/status codes
class AgentTransformResponse(APIResponse):
    agent_response: Optional[RagflowTransformAgentResponse] = None
    code: str


@cbv(view)
class ChatAgentRoute(CriaRoute):
    ResponseModel = AgentTransformResponse

    @view.post(
    path="/models/ragflow/{model_id}/agents/transform",
        name="Transform a query using chat history",
        summary="Transform a query using chat history",
        description="Modify the query to include chat history as part of the query",
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

    async def execute(self, request: Request, model_id: int, config: RagflowTransformAgentConfig) -> AgentTransformResponse:
        agent = RagflowTransformAgent(
            criadex=request.app.criadex,
            llm_model_id=model_id,
            model_config=config
        )
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully queried the Ragflow model!",
            agent_response=await agent.execute(
               config=config
            )
        )


__all__ = ["view"]
