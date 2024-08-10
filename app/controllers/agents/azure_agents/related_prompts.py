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
from app.core.config import QUERY_MODEL_RATE_LIMIT_DAY, QUERY_MODEL_RATE_LIMIT_HOUR, QUERY_MODEL_RATE_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import model_query_limiter
from criadex.agent.azure.related_prompts import RelatedPromptsGenerationAgent, RelatedPromptsGenerationAgentResponse
from criadex.agent.azure_agent import LLMAgentModelConfig
from criadex.index.llama_objects.models import EmptyPromptError, ContentFilterError
from criadex.schemas import ModelNotFoundError

view = APIRouter()


class AgentRelatedPromptsGenerationResponse(APIResponse):
    agent_response: Optional[RelatedPromptsGenerationAgentResponse] = None
    code: Union[SUCCESS, NOT_FOUND, INVALID_MODEL, INVALID_REQUEST, OPENAI_FILTER, ERROR]


class RelatedPromptsGenerationAgentConfig(LLMAgentModelConfig):
    llm_prompt: str
    llm_reply: str


@cbv(view)
class RelatedPromptsGenerationAgentRoute(CriaRoute):
    ResponseModel = AgentRelatedPromptsGenerationResponse

    @view.post(
        path="/models/azure/{model_id}/agents/related_prompts",
        name="Use the Related Prompts generation agent",
        summary="Use the Related Prompts generation agent",
        description="Use the Related Prompts generation agent",
    )
    @catch_exceptions(
        ResponseModel
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
        ModelNotFoundError,
        ResponseModel(
            code="NOT_FOUND",
            status=404,
            message="The requested model ID does not exist!",
        )
    )
    @exception_response(
        ValueError,
        ResponseModel(
            code="INVALID_MODEL",
            status=400,
            message="The model supplied is not a valid LLM model, though it is an LLM model."
        ),
        log_error=True
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
    async def execute(
            self,
            request: Request,
            model_id: int,
            config: RelatedPromptsGenerationAgentConfig
    ) -> ResponseModel:
        agent: RelatedPromptsGenerationAgent = RelatedPromptsGenerationAgent(
            criadex=request.app.criadex,
            llm_model_id=model_id,
            model_config=LLMAgentModelConfig(**config.dict()),
        )

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully generated related prompts",
            agent_response=await agent.execute(
                llm_prompt=config.llm_prompt,
                llm_reply=config.llm_reply
            )
        )


__all__ = ["view"]
