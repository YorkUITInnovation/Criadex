from typing import Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.models.generic import GenericModelsModel

view = APIRouter()


class GenericModelListResponse(APIResponse):
    code: Union[SUCCESS, ERROR]
    models: list[GenericModelsModel] = []


@cbv(view)
class ListGenericModelsRoute(CriaRoute):
    ResponseModel = GenericModelListResponse

    @view.get(
        path="/models/{provider_type}/list",
        name="List Generic Models",
        summary="List provider models",
        description="List model configs for extensible providers (ollama/openai/anthropic/etc).",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
            self,
            request: Request,
            provider_type: str,
    ) -> ResponseModel:
        provider_type = provider_type.lower()
        if provider_type in {"azure", "cohere"}:
            models = []
        else:
            models = [
                model
                for model in await request.app.criadex.list_generic_models()
                if model.provider_type == provider_type
            ]

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully listed models",
            models=models
        )


__all__ = ["view", "GenericModelListResponse"]
