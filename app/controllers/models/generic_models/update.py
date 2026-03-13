from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.models.generic import GenericModelsModel

view = APIRouter()


class GenericModelUpdateConfig(BaseModel):
    """Partial config for update."""
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_model: Optional[str] = None

    class Config:
        extra = "allow"


class GenericModelUpdateResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]
    model: Optional[GenericModelsModel] = None


@cbv(view)
class UpdateGenericModelRoute(CriaRoute):
    ResponseModel = GenericModelUpdateResponse

    @view.patch(
        path="/models/{provider_type}/{model_id}/update",
        name="Update a Generic Model",
        summary="Update model config",
        description="Update model config for ollama, openai, anthropic, etc.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
        self,
        request: Request,
        provider_type: str,
        model_id: int,
        model_config: GenericModelUpdateConfig
    ) -> ResponseModel:
        if provider_type.lower() in ("azure", "cohere"):
            raise HTTPException(
                status_code=404,
                detail="Use /models/azure/{id}/update or /models/cohere/{id}/update."
            )
        db = request.app.criadex.mysql_api
        existing = await db.generic_models.retrieve(model_id=model_id)
        if not existing or existing.provider_type != provider_type.lower():
            return self.ResponseModel(
                code="NOT_FOUND",
                status=404,
                message="The requested model does not exist.",
                model=None
            )
        config_dict = model_config.model_dump(exclude_none=True)
        merged = {**existing.config, **config_dict}
        updated = await db.generic_models.update(model_id=model_id, config=merged)
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully updated the model.",
            model=updated
        )


__all__ = ["view", "GenericModelUpdateResponse"]
