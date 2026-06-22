"""

Sync Ragflow tenant models into the Criadex registry.

"""

from typing import Union, Optional

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, ERROR
from app.core.route import CriaRoute

view = APIRouter()


class RagflowSyncStats(BaseModel):
    created: int = 0
    updated: int = 0
    removed: int = 0
    skipped: int = 0


class RagflowSyncResponse(APIResponse):
    code: Union[SUCCESS, ERROR]
    stats: Optional[RagflowSyncStats] = None


@cbv(view)
class RagflowSyncRoute(CriaRoute):
    ResponseModel = RagflowSyncResponse

    @view.post(
        path="/models/ragflow/sync",
        name="Sync Ragflow Models",
        summary="Sync Ragflow tenant LLM models into Criadex",
        description=(
            "Reads active models from Ragflow tenant_llm and mirrors them into "
            "the generic model registry with provider_type=ragflow."
        ),
    )
    @catch_exceptions(ResponseModel)
    async def execute(self, request: Request) -> ResponseModel:
        stats = await request.app.criadex.sync_ragflow_models()
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully synced Ragflow models.",
            stats=RagflowSyncStats(**stats),
        )


__all__ = ["view", "RagflowSyncResponse", "RagflowSyncStats"]
