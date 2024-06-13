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

from app.controllers.models.azure_models.about import AzureModelAboutResponse
from app.controllers.schemas import catch_exceptions, exception_response, SUCCESS, NOT_FOUND, \
    ERROR, DUPLICATE
from app.core.route import CriaRoute
from criadex.database.tables.models.azure import AzureModelsModel, AzureModelsPartialBaseModel
from criadex.schemas import ModelExistsError, ModelNotFoundError

view = APIRouter()


class AzureModelUpdateResponse(AzureModelAboutResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR, DUPLICATE]


@cbv(view)
class UpdateAzureModelRoute(CriaRoute):
    ResponseModel = AzureModelUpdateResponse

    @view.patch(
        path="/models/azure/{model_id}/update",
        name="Update an Azure Model",
        summary="Update an Azure Model",
        description="Update an Azure OpenAI model config in the database.",
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
            message="Error updating, the new deployment already exists in the database with that Azure resource!",
            model=None
        )
    )
    async def execute(
            self,
            request: Request,
            model_id: int,
            model_config: AzureModelsPartialBaseModel
    ) -> ResponseModel:
        # Get model
        model: AzureModelsModel = await request.app.criadex.about_azure_model(model_id=model_id)

        # Update fields
        model.api_key = model_config.api_key,
        model.api_deployment = model_config.api_deployment
        model.api_version = model_config.api_version
        model.api_resource = model_config.api_resource

        # Update DB
        model: Optional[AzureModelsModel] = await request.app.criadex.update_azure_model(config=model)

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully updated the model.",
            model=model
        )


__all__ = ["view", "AzureModelUpdateResponse"]
