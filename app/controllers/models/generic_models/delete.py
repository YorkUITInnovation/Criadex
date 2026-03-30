from typing import Union

from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, NOT_FOUND, ERROR
from app.core.route import CriaRoute

view = APIRouter()


class GenericModelDeleteResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]


@cbv(view)
class DeleteGenericModelRoute(CriaRoute):
    ResponseModel = GenericModelDeleteResponse

    @view.delete(
        path="/models/{provider_type}/{model_id}/delete",
        name="Delete a Generic Model",
        summary="Delete model config",
        description="Delete model config for ollama, openai, anthropic, etc.",
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
                detail="Use /models/azure/{id}/delete or /models/cohere/{id}/delete."
            )
        db = request.app.criadex.mysql_api
        existing = await db.generic_models.retrieve(model_id=model_id)
        if not existing or existing.provider_type != provider_type.lower():
            return self.ResponseModel(
                code="NOT_FOUND",
                status=404,
                message="The requested model does not exist."
            )
        await db.generic_models.delete(model_id=model_id)
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully deleted the model."
        )


__all__ = ["view", "GenericModelDeleteResponse"]
