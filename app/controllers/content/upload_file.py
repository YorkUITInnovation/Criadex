"""
Native file upload endpoint — replaces CriaParse.

Accepts a raw multipart file and sends it directly to Ragflow for native parsing.
Ragflow handles chunking/embedding; no pre-parsed nodes are needed.
"""

from typing import Optional, Union
import logging

from fastapi import APIRouter, UploadFile, File, Form
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, DUPLICATE, ERROR
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError, DocumentExistsError

logger = logging.getLogger(__name__)

view = APIRouter()


class NativeFileUploadResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, DUPLICATE, ERROR]
    document_name: Optional[str] = None


@cbv(view)
class NativeFileUploadRoute(CriaRoute):
    ResponseModel = NativeFileUploadResponse

    @view.post(
        path="/groups/{group_name}/content/upload/file",
        name="Upload Raw File (Native Ragflow Parse)",
        summary="Upload a raw file for native Ragflow parsing",
        description="Upload any file (PDF, DOCX, HTML, TXT …) directly to Ragflow. "
                    "Ragflow's native parser chunks and indexes it. Replaces CriaParse.",
    )
    @catch_exceptions(ResponseModel)
    @exception_response(
        DocumentExistsError,
        ResponseModel(
            code="DUPLICATE",
            status=409,
            message="A document with this name already exists. Delete it first or use a different filename.",
        ),
    )
    async def execute(
        self,
        request: Request,
        group_name: str,
        file: UploadFile = File(...),
        filename_override: Optional[str] = Form(default=None),
        strategy: Optional[str] = Form(default=None),
    ) -> ResponseModel:
        try:
            file_name = filename_override or file.filename or "upload"
            file_bytes = await file.read()
            content_type = file.content_type or ""

            await request.app.criadex.insert_native_file(
                group_name=group_name,
                file_name=file_name,
                file_bytes=file_bytes,
                strategy=strategy,
                content_type=content_type,
            )

            return self.ResponseModel(
                code="SUCCESS",
                status=200,
                message="File queued for native Ragflow parsing.",
                document_name=file_name,
            )
        except GroupNotFoundError:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message=f"The requested index group '{group_name}' was not found.",
            )
        except DocumentExistsError:
            return self.ResponseModel(
                code="DUPLICATE",
                status=409,
                message="A document with this name already exists.",
            )
        except Exception as exc:
            logger.error(
                "Native file upload failed for group '%s': %s",
                group_name,
                exc,
                exc_info=True,
            )
            return self.ResponseModel(
                code="ERROR",
                status=500,
                message=f"Unexpected error: {exc}",
            )


__all__ = ["view"]
