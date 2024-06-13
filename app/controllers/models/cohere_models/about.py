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

from app.controllers.models.azure_models.about import AzureModelAboutResponse
from app.controllers.schemas import catch_exceptions, exception_response
from app.core.route import CriaRoute
from criadex.database.tables.models.cohere import CohereModelsModel
from criadex.schemas import ModelNotFoundError

view = APIRouter()


class CohereModelAboutResponse(AzureModelAboutResponse):
    model: Optional[CohereModelsModel] = None


@cbv(view)
class AboutCohereModelRoute(CriaRoute):
    ResponseModel = CohereModelAboutResponse

    @view.get(
        path="/models/cohere/{model_id}/about",
        name="Get Cohere Model Info",
        summary="Get Cohere Model Info",
        description="Retrieve some basic info about a Cohere Model.",
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
            model=None
        )
    )
    async def execute(
            self,
            request: Request,
            model_id: int
    ) -> ResponseModel:
        model: CohereModelsModel = await request.app.criadex.about_cohere_model(model_id=model_id)

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully retrieved the model config",
            model=model
        )


__all__ = ["view"]
