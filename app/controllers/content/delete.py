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

from typing import Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, \
    FILE_NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError, DocumentNotFoundError

view = APIRouter()


class ContentDeleteResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, FILE_NOT_FOUND, ERROR]


@cbv(view)
class DeleteContentRoute(CriaRoute):
    ResponseModel = ContentDeleteResponse

    @view.delete(
        path="/groups/{group_name}/content/delete",
        name="Delete Index Content",
        summary="Delete Index Content",
        description="Delete file content from the API. The requested file will be removed from the index group & deleted.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        GroupNotFoundError,
        ResponseModel(
            code="GROUP_NOT_FOUND",
            status=404,
            message="Could not find The requested index group."
        )
    )
    @exception_response(
        DocumentNotFoundError,
        ResponseModel(
            code="FILE_NOT_FOUND",
            status=404,
            message="Requested content does not exist in the database."
        )
    )
    async def execute(
            self,
            request: Request,
            group_name: str,
            document_name: str
    ) -> ResponseModel:
        # Try to delete it
        await request.app.criadex.delete_file(
            group_name=group_name,
            document_name=document_name
        )

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully deleted & de-indexed the content."
        )


__all__ = ["view"]
