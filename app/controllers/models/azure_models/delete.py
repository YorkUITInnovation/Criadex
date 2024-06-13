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

from typing import Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, NOT_FOUND, MODEL_IN_USE, \
    ERROR
from app.core.route import CriaRoute
from criadex.schemas import ModelNotFoundError, ModelInUseError

view = APIRouter()


class AzureModelDeleteResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, MODEL_IN_USE, ERROR]


@cbv(view)
class DeleteAzureModelRoute(CriaRoute):
    ResponseModel = AzureModelDeleteResponse

    @view.delete(
        path="/models/azure/{model_id}/delete",
        name="Delete an Azure Model",
        summary="Delete an Azure Model",
        description="Delete an Azure OpenAI model config from the database.",
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
        ModelInUseError,
        ResponseModel(
            code="MODEL_IN_USE",
            status=409,
            message="The requested model can't be deleted while it's still in use by >=1 index!"
        )
    )
    async def execute(
            self,
            request: Request,
            model_id: int
    ) -> ResponseModel:
        await request.app.criadex.delete_azure_model(model_id=model_id)

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully deleted the model"
        )


__all__ = ["view", "AzureModelDeleteResponse"]
