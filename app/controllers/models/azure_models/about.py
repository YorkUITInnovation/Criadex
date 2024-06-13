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

from typing import Union, Optional

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.models.azure import AzureModelsModel
from criadex.schemas import ModelNotFoundError

view = APIRouter()


class AzureModelAboutResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]
    model: Optional[AzureModelsModel] = None


@cbv(view)
class AboutAzureModelRoute(CriaRoute):
    ResponseModel = AzureModelAboutResponse

    @view.get(
        path="/models/azure/{model_id}/about",
        name="Get Azure Model Info",
        summary="Get Azure Model Info",
        description="Retrieve some basic info about an Azure Model.",
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
        model: AzureModelsModel = await request.app.criadex.about_azure_model(model_id=model_id)

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully retrieved the model config",
            model=model
        )


__all__ = ["view", "AzureModelAboutResponse"]
