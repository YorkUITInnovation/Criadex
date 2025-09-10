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

from app.controllers.models.azure_models.update import AzureModelUpdateResponse
from app.controllers.schemas import catch_exceptions, exception_response
from app.core.route import CriaRoute
from criadex.database.tables.models.cohere import CohereModelsPartialBaseModel, CohereModelsModel
from criadex.schemas import ModelExistsError, ModelNotFoundError

view = APIRouter()


class CohereModelUpdateResponse(AzureModelUpdateResponse):
    # Override type of `model` to CohereModelsModel for accurate validation
    model: Optional[CohereModelsModel] = None


@cbv(view)
class UpdateCohereModelRoute(CriaRoute):
    ResponseModel = CohereModelUpdateResponse

    @view.patch(
        path="/models/cohere/{model_id}/update",
        name="Update a Cohere Model",
        summary="Update a Cohere Model",
        description="Update a Cohere model config in the database.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        ModelNotFoundError,
        ResponseModel(
            code="NOT_FOUND",
            status=404,
            message="The requested model ID does not exist!"
        )
    )
    @exception_response(
        ModelExistsError,
        ResponseModel(
            code="DUPLICATE",
            status=409,
            message="Error updating, the model for that API key already exists!",
            model=None
        )
    )
    async def execute(
            self,
            request: Request,
            model_id: int,
            model_config: CohereModelsPartialBaseModel
    ) -> ResponseModel:
        # Get model
        model: CohereModelsModel = await request.app.criadex.about_cohere_model(model_id=model_id)

        # Update fields
        if model_config.api_key is not None:
            model.api_key = model_config.api_key

        # Update DB
        await request.app.criadex.update_cohere_model(config=model)
        updated: CohereModelsModel = await request.app.criadex.about_cohere_model(model_id=model.id)

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully updated the model.",
            model=updated
        )


__all__ = ["view"]
