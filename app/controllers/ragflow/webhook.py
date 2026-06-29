"""
Ragflow webhook and reconcile endpoints.
"""

from typing import Optional, Dict, Any
import os
import asyncio

from fastapi import APIRouter
from fastapi_restful.cbv import cbv
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse
from app.core.route import CriaRoute

view = APIRouter(prefix="/ragflow", tags=["Ragflow"])


class RagflowWebhookResponse(APIResponse):
    code: str
    stats: Optional[Dict[str, Any]] = None


class WebhookRequest(BaseModel):
    event: Optional[str] = None
    resource: Optional[Dict[str, Any]] = None


@cbv(view)
class RagflowWebhookRoute(CriaRoute):
    ResponseModel = RagflowWebhookResponse

    @view.post(
        path="/webhook",
        name="Ragflow Webhook Receiver",
        summary="Receive Ragflow webhooks and trigger reconcile",
        description="Accepts basic Ragflow events and schedules a reconcile of KB links.",
    )
    @catch_exceptions(ResponseModel)
    async def webhook(self, request: Request, payload: WebhookRequest) -> RagflowWebhookResponse:
        # Validate Bearer token against configured RAGFLOW_API_KEY for security
        auth = request.headers.get("authorization", "")
        token = ""
        if auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1].strip()
        if not token or token != os.getenv("RAGFLOW_API_KEY", "").strip():
            return self.ResponseModel(code="ERROR", status=401, message="Unauthorized webhook", stats=None)

        # Schedule reconcile in background to respond quickly
        try:
            kb_sync = getattr(request.app.criadex, "kb_sync", None)
            if kb_sync is None:
                return self.ResponseModel(code="ERROR", status=500, message="KB sync not configured", stats=None)

            # For now, always trigger full reconcile (could be optimized per-event)
            asyncio.create_task(kb_sync.reconcile_all_groups())
            return self.ResponseModel(code="SUCCESS", status=202, message="Reconcile scheduled", stats=None)
        except Exception as exc:
            return self.ResponseModel(code="ERROR", status=500, message=f"Webhook handling failed: {exc}", stats=None)

    @view.post(
        path="/reconcile",
        name="Ragflow Reconcile",
        summary="Run a full reconcile between Ragflow and Criadex Group links",
        description="Manually trigger reconciliation: upsert missing links and remove stale links.",
    )
    @catch_exceptions(ResponseModel)
    async def reconcile(self, request: Request) -> RagflowWebhookResponse:
        kb_sync = getattr(request.app.criadex, "kb_sync", None)
        if kb_sync is None:
            return self.ResponseModel(code="ERROR", status=500, message="KB sync not configured", stats=None)

        stats = await kb_sync.reconcile_all_groups()
        return self.ResponseModel(code="SUCCESS", status=200, message="Reconcile completed", stats=stats)

    @view.get(
        path="/link/{group_name}",
        name="Get Group Ragflow Link",
        summary="Return the stored GroupRagflowLinks entry for a group (test-only)",
        description="Returns GroupRagflowLinks row for the given group_name. Intended for tests. Requires master API key.",
    )
    @catch_exceptions(ResponseModel)
    async def get_link(self, request: Request, group_name: str) -> RagflowWebhookResponse:
        kb_sync = getattr(request.app.criadex, "kb_sync", None)
        if kb_sync is None:
            return self.ResponseModel(code="ERROR", status=500, message="KB sync not configured", stats=None)

        link = await kb_sync._read_link(group_name)
        if not link:
            return self.ResponseModel(code="SUCCESS", status=200, message="No link found", stats=None)

        # Return link fields in stats for convenience
        stats = {
            "ragflow_dataset_id": link.get("ragflow_dataset_id"),
            "ragflow_dataset_name": link.get("ragflow_dataset_name"),
            "ragflow_chat_id": link.get("ragflow_chat_id"),
        }
        return self.ResponseModel(code="SUCCESS", status=200, message="Link found", stats=stats)

    # Implement abstract execute to satisfy CriaRoute ABC used by cbv wrapper
    async def execute(self) -> RagflowWebhookResponse:
        """Dummy execute implementation to satisfy CriaRoute abstractmethod.
        Not used; webhook and reconcile are the actual endpoints.
        """
        return self.ResponseModel(code="SUCCESS", status=200, message="OK", stats={})


__all__ = ["view", "RagflowWebhookResponse", "WebhookRequest"]
