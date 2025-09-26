"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Isaac Kogan
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""

from typing import Optional, Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from pydantic import ValidationError
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, INVALID_FILE_DATA, DUPLICATE, ERROR
from app.core.route import CriaRoute
from criadex.group import Group
from criadex.index.base_api import ContentUploadConfig
from criadex.index.schemas import Bundle, BundleConfig
from criadex.schemas import GroupNotFoundError, DocumentExistsError

view = APIRouter()


class ContentUploadResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, INVALID_FILE_DATA, DUPLICATE, ERROR]
    token_usage: Optional[int] = None


@cbv(view)
class UploadContentRoute(CriaRoute):
    ResponseModel = ContentUploadResponse

    @view.post(
        path="/groups/{group_name}/content/upload",
        name="Upload Index Content",
        summary="Upload Index Content",
        description="Upload file content to the API. Data sent will be indexed & stored.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        DocumentExistsError,
        ResponseModel(
            code="DUPLICATE",
            status=409,
            message="Requested content already exists in the database."
        )

    )
    async def execute(
            self,
            request: Request,
            group_name: str,
            file: ContentUploadConfig
    ) -> ResponseModel:

        try:
            token_usage = await request.app.criadex.insert_file(
                group_name=group_name,
                file_name=file.file_name,
                file_contents=file.file_contents
            )
            return self.ResponseModel(
                code="SUCCESS",
                status=200,
                message="Successfully uploaded & indexed the content.",
                token_usage=token_usage
            )
        except GroupNotFoundError:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message=f"The requested index group '{group_name}' was not found"
            )
        except DocumentExistsError:
            return self.ResponseModel(
                code="DUPLICATE",
                status=409,
                message="Requested content already exists in the database."
            )
        except Exception as e:
            # Catch any other unexpected errors
            return self.ResponseModel(
                code="ERROR",
                status=500,
                message=f"An unexpected error occurred: {e}"
            )


__all__ = ["view"]
