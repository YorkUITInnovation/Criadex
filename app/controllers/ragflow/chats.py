from typing import Optional
from fastapi import APIRouter
from fastapi_restful.cbv import cbv
from starlette.requests import Request
from pydantic import BaseModel

from app.controllers.schemas import catch_exceptions, APIResponse
from criadex.schemas import SUCCESS
from app.core.route import CriaRoute

view = APIRouter(prefix="/ragflow", tags=["Ragflow"])


class EnsureDialogRequest(BaseModel):
    tenant_id: Optional[str] = None
    llm_id: Optional[str] = "gpt-3.5-turbo"


class EnsureDialogResponse(APIResponse):
    chat_id: Optional[str] = None
    created: Optional[bool] = False


@cbv(view)
class RagflowChatsRoute(CriaRoute):
    ResponseModel = EnsureDialogResponse

    @view.post(
        path="/chats/{chat_id}/ensure",
        name="Ensure Ragflow Dialog Exists",
        summary="Ensure a Ragflow dialog exists for a chat ID",
        description="Ensure a Ragflow dialog exists. Creates it if it doesn't exist.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
        self,
        request: Request,
        chat_id: str,
        payload: EnsureDialogRequest
    ) -> ResponseModel:
        """Ensure a dialog exists in Ragflow for the given chat_id."""
        try:
            from criadex.index.ragflow_objects.chat import RagflowChatAgent
            
            agent = RagflowChatAgent()
            success = await agent.ensure_dialog_exists(
                chat_id=chat_id,
                tenant_id=payload.tenant_id,
                llm_id=payload.llm_id or "gpt-3.5-turbo"
            )
            
            return self.ResponseModel(
                code=SUCCESS,
                status=200,
                message="Dialog ensured successfully" if success else "Failed to ensure dialog",
                chat_id=chat_id,
                created=True
            )
        except Exception as e:
            return self.ResponseModel(
                code="ERROR",
                status=500,
                message=f"Failed to ensure dialog: {str(e)}",
                chat_id=chat_id,
                created=False
            )


__all__ = ["view"]
