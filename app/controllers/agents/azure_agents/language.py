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
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, ERROR
from app.core.config import QUERY_MODEL_RATE_LIMIT_DAY, QUERY_MODEL_RATE_LIMIT_HOUR, QUERY_MODEL_RATE_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import model_query_limiter
from criadex.agent.azure.language import LanguageAgentResponse, LanguageAgent

view = APIRouter()


class AgentLanguageResponse(APIResponse):
    agent_response: Optional[LanguageAgentResponse] = None
    code: Union[SUCCESS, ERROR]


class LanguageAgentConfig(BaseModel):
    prompt: str


@cbv(view)
class LanguageAgentRoute(CriaRoute):
    ResponseModel = AgentLanguageResponse
    AGENT = LanguageAgent()

    # noinspection PyUnusedLocal
    @view.post(
        path="/models/azure/{model_id}/agents/language",
        name="Use the Language agent",
        summary="Use the Language agent",
        description="Use the Language agent",
    )
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_DAY)
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_HOUR)
    @model_query_limiter.limit(QUERY_MODEL_RATE_LIMIT_MINUTE)
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,  # Request IS useful, for the limiter
            model_id: int,
            config: LanguageAgentConfig
    ) -> ResponseModel:
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully detected the language.",
            agent_response=self.AGENT.execute(config.prompt)
        )


__all__ = ["view"]
