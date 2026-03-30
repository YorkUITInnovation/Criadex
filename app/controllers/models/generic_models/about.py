from typing import Optional, Union

from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.models.generic import GenericModelsModel

view = APIRouter()


class GenericModelAboutResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]
    model: Optional[GenericModelsModel] = None


@cbv(view)
class AboutGenericModelRoute(CriaRoute):
    ResponseModel = GenericModelAboutResponse

    @view.get(
        path="/models/{provider_type}/{model_id}/about",
        name="Get Generic Model Info",
        summary="Get model info for a provider",
        description="Retrieve model config for ollama, openai, anthropic, etc.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
        self,
        request: Request,
        provider_type: str,
        model_id: int
    ) -> ResponseModel:
        if provider_type.lower() in ("azure", "cohere"):
            raise HTTPException(
                status_code=404,
                detail="Use /models/azure/{id}/about or /models/cohere/{id}/about."
            )
        db = request.app.criadex.mysql_api
        model = await db.generic_models.retrieve(model_id=model_id)
        if not model or model.provider_type != provider_type.lower():
            return self.ResponseModel(
                code="NOT_FOUND",
                status=404,
                message="The requested model does not exist.",
                model=None
            )
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully retrieved the model config",
            model=model
        )


__all__ = ["view", "GenericModelAboutResponse"]
