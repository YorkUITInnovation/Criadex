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

from typing import Optional

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.agents.azure_agents.intents import AgentIntentsResponse
from app.controllers.schemas import catch_exceptions, exception_response
from app.core.config import QUERY_MODEL_RATE_LIMIT_HOUR, QUERY_MODEL_RATE_LIMIT_DAY, QUERY_MODEL_RATE_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import model_query_limiter
from criadex.agent.cohere.rerank import RerankAgentResponse, RerankAgent, RerankAgentConfig
from criadex.index.llama_objects.models import EmptyPromptError
from criadex.schemas import ModelNotFoundError

view = APIRouter()


class AgentRerankResponse(AgentIntentsResponse):
    agent_response: Optional[RerankAgentResponse] = None


@cbv(view)
class RerankAgentRoute(CriaRoute):
    ResponseModel = AgentRerankResponse

    @view.post(
        path="/models/cohere/{model_id}/agents/rerank",
        name="Use the Rerank agent",
        summary="Use the Rerank agent",
        description="Use the Language agent",
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
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_DAY)
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_HOUR)
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_MINUTE)
    async def execute(
            self,
            request: Request,  # Request IS useful, for the limiter
            model_id: int,
            config: RerankAgentConfig
    ) -> ResponseModel:
        agent: RerankAgent = RerankAgent(
            criadex=request.app.criadex,
            cohere_model_id=model_id
        )

        response: RerankAgentResponse = await agent.execute(config)

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully re-ranked the nodes",
            agent_response=response
        )


__all__ = ["view"]
