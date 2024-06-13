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
from app.core.database.api import AuthDatabaseAPI
from app.core.database.tables.auth import AuthorizationsModel
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError

view = APIRouter()


class GroupAuthDeleteResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, NOT_FOUND, ERROR]


@cbv(view)
class DeleteGroupAuthRoute(CriaRoute):
    ResponseModel = GroupAuthDeleteResponse

    @view.delete(
        path="/group_auth/{group_name}/delete",
        name="Delete index authorizations",
        summary="Delete an authorization on an index group",
        description="Remove the specified authorization on an index group",
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
        database: AuthDatabaseAPI = request.app.auth

        group_id: int = await request.app.criadex.get_id(name=group_name)

        # Now get the key's ID
        auth_model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(key=api_key)

        if auth_model is None:
            return self.ResponseModel(
                code="NOT_FOUND",
                status=404,
                message="API key not found"
            )

        if not await database.group_authorizations.exists(
                group_id=group_id, authorization_id=auth_model.id
        ):
            return self.ResponseModel(
                status=404,
                code="SUCCESS",
                message="The key is not authorized on this index!"
            )

        # Now delete it
        await database.group_authorizations.delete_group_authorization(
            group_id=group_id, authorization_id=auth_model.id
        )

        return self.ResponseModel(
            status=200,
            code="SUCCESS"
        )


__all__ = ["view"]
