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

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError

view = APIRouter()


class GroupDeleteResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, ERROR]


@cbv(view)
class DeleteGroupRoute(CriaRoute):
    ResponseModel = GroupDeleteResponse

    @view.delete(
        path="/groups/{group_name}/delete",
        name="Delete a Group",
        summary="Delete a Group",
        description="Delete a group on the Criadex indexing server.",
    )
    @exception_response(
        GroupNotFoundError,
        ResponseModel(
            code="GROUP_NOT_FOUND",
            status=404,
            message="The requested index group does not exist!"
        )
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            group_name: str
    ) -> ResponseModel:
        group_id = await request.app.criadex.get_id(name=group_name, throw_not_found=False)
        if group_id is None:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message="The requested index group does not exist!"
            )
        await request.app.auth.group_authorizations.delete_all_by_group_id(group_id=group_id)

        await request.app.criadex.delete(name=group_name)

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully deleted the index group."
        )
