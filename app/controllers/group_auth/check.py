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
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, \
    NOT_FOUND, ERROR
from app.core.database.tables.auth import AuthorizationsModel
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError

view = APIRouter()


class GroupAuthCheckResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, NOT_FOUND, ERROR]
    authorized: Optional[bool] = None
    master: Optional[bool] = None


@cbv(view)
class CheckGroupAuthRoute(CriaRoute):
    ResponseModel = GroupAuthCheckResponse

    @view.get(
        path="/group_auth/{group_name}/check",
        name="Check index authorization",
        summary="Check if an authorization is authorized on an index group",
        description="Check if a given authorization is authorized to access an index group",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        GroupNotFoundError,
        ResponseModel(
            code="GROUP_NOT_FOUND",
            status=404,
            message="Group not found"
        )

    )
    async def execute(
            self,
            request: Request,
            group_name: str,
            api_key: str
    ) -> ResponseModel:
        group_id: int = await request.app.criadex.get_id(name=group_name)

        # Now get the key's ID
        auth_model: Optional[AuthorizationsModel] = await request.app.auth.authorizations.retrieve(key=api_key)

        if auth_model is None:
            return self.ResponseModel(
                code="NOT_FOUND",
                status=404,
                message="API key not found"
            )

        # If it's master, it's ALWAYS authorized
        if auth_model.master:
            return self.ResponseModel(
                status=200,
                code="SUCCESS",
                authorized=True,
                master=auth_model.master
            )

        # Now check if it's authorized
        status: bool = await request.app.auth.group_authorizations.exists(
            group_id=group_id, authorization_id=auth_model.id
        )

        return self.ResponseModel(
            status=200,
            code="SUCCESS",
            authorized=status,
            master=auth_model.master
        )


__all__ = ["view"]
