from typing import Optional

from fastapi import APIRouter, Security
from fastapi_utils.cbv import cbv
from pydantic import BaseModel

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS
from app.core import config
from app.core.route import CriaRoute
from app.core.schemas import AppMode
from app.core.security import get_api_key_master

view = APIRouter(
    dependencies=[Security(get_api_key_master)] if config.APP_MODE == AppMode.PRODUCTION else []
)


class ModelDedupeResponse(APIResponse):
    code: SUCCESS
    merged_groups: int = 0
    deleted_models: int = 0


class ModelDedupeRequest(BaseModel):
    provider_type: Optional[str] = None
    api_model: Optional[str] = None


@cbv(view)
class DedupeModelsRoute(CriaRoute):
    ResponseModel = ModelDedupeResponse

    @view.post(
        path="/models/dedupe",
        name="Deduplicate generic models",
        summary="Merge duplicate generic models that share provider_type and api_model",
        description="Keeps the lowest model id, remaps Groups references, and deletes duplicates.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(self, request, payload: ModelDedupeRequest | None = None) -> ResponseModel:
        payload = payload or ModelDedupeRequest()
        db = request.app.criadex.mysql_api
        result = await db.generic_models.dedupe_duplicates(
            provider_type=payload.provider_type,
            api_model=payload.api_model,
        )
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Duplicate generic models merged.",
            merged_groups=result["merged_groups"],
            deleted_models=result["deleted_models"],
        )


__all__ = ["view", "ModelDedupeResponse"]
