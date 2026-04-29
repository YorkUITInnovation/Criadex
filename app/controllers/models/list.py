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

from typing import Union, Optional

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, ERROR
from app.core.route import CriaRoute

view = APIRouter()


class ModelListItem(BaseModel):
    id: int
    provider_type: str
    api_model: Optional[str] = None
    api_resource: Optional[str] = None
    api_deployment: Optional[str] = None
    config: Optional[dict] = None


class ModelListResponse(APIResponse):
    code: Union[SUCCESS, ERROR]
    models: list[ModelListItem] = []


@cbv(view)
class ListModelsRoute(CriaRoute):
    ResponseModel = ModelListResponse

    @view.get(
        path="/models/list",
        name="List All Models",
        summary="List all provider models",
        description="List all models across Azure, Cohere, and generic providers.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
            self,
            request: Request,
    ) -> ResponseModel:
        azure_models = await request.app.criadex.list_azure_models()
        cohere_models = await request.app.criadex.list_cohere_models()
        generic_models = await request.app.criadex.list_generic_models()

        output: list[ModelListItem] = []

        for model in azure_models:
            output.append(ModelListItem(
                id=model.id,
                provider_type="azure",
                api_model=model.api_model,
                api_resource=model.api_resource,
                api_deployment=model.api_deployment,
            ))

        for model in cohere_models:
            output.append(ModelListItem(
                id=model.id,
                provider_type="cohere",
                api_model=model.api_model,
            ))

        for model in generic_models:
            output.append(ModelListItem(
                id=model.id,
                provider_type=model.provider_type,
                api_model=(model.config or {}).get("api_model"),
                config=model.config,
            ))

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully listed models",
            models=output
        )


__all__ = ["view", "ModelListResponse", "ModelListItem"]
