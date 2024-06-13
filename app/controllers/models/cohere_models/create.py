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

from app.controllers.models.azure_models.create import AzureModelCreateResponse
from app.controllers.schemas import catch_exceptions, exception_response
from app.core.route import CriaRoute
from criadex.database.tables.models.cohere import CohereModelsModel, CohereModelsBaseModel
from criadex.schemas import ModelExistsError

view = APIRouter()


class CohereModelCreateResponse(AzureModelCreateResponse):
    model: Optional[CohereModelsModel] = None


@cbv(view)
class CreateCohereModelRoute(CriaRoute):
    ResponseModel = CohereModelCreateResponse

    @view.post(
        path="/models/cohere/create",
        name="Add a Cohere Model",
        summary="Add a Cohere Model",
        description="Add a Cohere model config to the database.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        ModelExistsError,
        ResponseModel(
            code="DUPLICATE",
            status=409,
            message="That model already exists for that Cohere API key!",
            model=None
        )
    )
    async def execute(
            self,
            request: Request,
            model_config: CohereModelsBaseModel
    ) -> ResponseModel:
        model: Optional[CohereModelsModel] = await request.app.criadex.insert_cohere_model(config=model_config)

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully created the model. Model ID returned in payload.",
            model=model
        )


__all__ = ["view"]
