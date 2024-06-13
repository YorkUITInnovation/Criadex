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

from typing import List, Union, Optional

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError

view = APIRouter()


class ContentListResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, ERROR]
    files: Optional[List[str]] = None


@cbv(view)
class ListContentRoute(CriaRoute):
    ResponseModel = ContentListResponse

    @view.get(
        path="/groups/{group_name}/content/list",
        name="List Index Content",
        summary="List Index Content",
        description="Get a list of files associated with this index. File content cannot be viewed.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        GroupNotFoundError,
        ResponseModel(
            code="GROUP_NOT_FOUND",
            status=404,
            message="Could not find The requested index group"
        )
    )
    async def execute(
            self,
            request: Request,
            group_name: str
    ) -> ResponseModel:
        files: List[str] = await request.app.criadex.list_files(
            group_name=group_name
        )

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully retrieved index content.",
            files=files
        )


__all__ = ["view"]
