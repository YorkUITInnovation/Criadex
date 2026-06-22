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
from criadex.models.usability import (
    infer_model_type,
    is_azure_model_usable,
    is_cohere_model_usable,
    is_generic_model_usable,
)

view = APIRouter()


class ModelListItem(BaseModel):
    id: int
    provider_type: str
    api_model: Optional[str] = None
    api_resource: Optional[str] = None
    api_deployment: Optional[str] = None
    config: Optional[dict] = None
    model_type: Optional[str] = None
    is_usable: bool = False
    display_name: Optional[str] = None


class ModelListResponse(APIResponse):
    code: Union[SUCCESS, ERROR]
    models: list[ModelListItem] = []


def _dedupe_cohere_models(models: list) -> list:
    """Keep one Cohere row per api_model (lowest id)."""
    best: dict[str, object] = {}
    for model in models:
        key = (model.api_model or "").lower()
        if not key:
            continue
        if key not in best or model.id < best[key].id:
            best[key] = model
    return list(best.values())


@cbv(view)
class ListModelsRoute(CriaRoute):
    ResponseModel = ModelListResponse

    @view.get(
        path="/models/list",
        name="List All Models",
        summary="List usable provider models",
        description=(
            "List configured models across Azure, Cohere, generic, and Ragflow providers. "
            "Ragflow tenant models are synced before listing. Placeholder seed models are excluded."
        ),
    )
    @catch_exceptions(ResponseModel)
    async def execute(
            self,
            request: Request,
    ) -> ResponseModel:
        try:
            await request.app.criadex.sync_ragflow_models()
        except Exception:
            # Listing should still work when Ragflow DB is temporarily unavailable.
            pass

        azure_models = await request.app.criadex.list_azure_models()
        cohere_models = _dedupe_cohere_models(await request.app.criadex.list_cohere_models())
        generic_models = await request.app.criadex.list_generic_models()

        output: list[ModelListItem] = []

        for model in azure_models:
            usable = is_azure_model_usable(model)
            model_type = infer_model_type("azure", model.api_model)
            output.append(ModelListItem(
                id=model.id,
                provider_type="azure",
                api_model=model.api_model,
                api_resource=model.api_resource,
                api_deployment=model.api_deployment,
                model_type=model_type,
                is_usable=usable,
                display_name=model.api_model if usable else None,
            ))

        for model in cohere_models:
            usable = is_cohere_model_usable(model)
            model_type = infer_model_type("cohere", model.api_model)
            output.append(ModelListItem(
                id=model.id,
                provider_type="cohere",
                api_model=model.api_model,
                model_type=model_type,
                is_usable=usable,
                display_name=model.api_model if usable else None,
            ))

        for model in generic_models:
            config = model.config or {}
            api_model = (config.get("api_model") or "").strip()
            usable = is_generic_model_usable(model)
            model_type = infer_model_type(model.provider_type, api_model, config)
            display_name = api_model
            if usable and (model.provider_type or "").lower() == "ragflow":
                factory = (config.get("llm_factory") or "").strip()
                display_name = f"{api_model} ({factory})" if factory else api_model

            merged_config = dict(config)
            merged_config["model_type"] = model_type

            output.append(ModelListItem(
                id=model.id,
                provider_type=model.provider_type,
                api_model=api_model or None,
                config=merged_config,
                model_type=model_type,
                is_usable=usable,
                display_name=display_name if usable else None,
            ))

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully listed models",
            models=output
        )


__all__ = ["view", "ModelListResponse", "ModelListItem"]
