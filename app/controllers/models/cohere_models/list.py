"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Kiarash Bashokian
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""

from typing import Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.models.cohere import CohereModelsModel

view = APIRouter()


class CohereModelListResponse(APIResponse):
    code: Union[SUCCESS, ERROR]
    models: list[CohereModelsModel] = []


@cbv(view)
class ListCohereModelsRoute(CriaRoute):
    ResponseModel = CohereModelListResponse

    @view.get(
        path="/models/cohere/list",
        name="List Cohere Models",
        summary="List Cohere Models",
        description="List all Cohere model configs.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
            self,
            request: Request,
    ) -> ResponseModel:
        models = await request.app.criadex.list_cohere_models()

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully listed Cohere models",
            models=models
        )


__all__ = ["view", "CohereModelListResponse"]
