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

"""

"""

from typing import Optional, List, Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, NOT_FOUND, ERROR
from app.core.database.api import AuthDatabaseAPI
from app.core.database.tables.auth import AuthorizationsModel
from app.core.database.tables.group_auth import GroupAuthorizationsModel
from app.core.route import CriaRoute
from criadex.database.tables.groups import GroupsModel

view = APIRouter()


class GroupAuthListResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]
    groups: Optional[List[GroupsModel]] = None


@cbv(view)
class ListGroupAuthRoute(CriaRoute):
    ResponseModel = GroupAuthListResponse

    @view.get(
        path="/group_auth/list",
        name="List authorized indexes",
        summary="List the index groups a user is authorized on",
        description="List the index groups a user is authorized on",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            api_key: str
    ) -> ResponseModel:
        # Get their auth model
        database: AuthDatabaseAPI = request.app.auth
        auth_model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(api_key)

        # Key DNE
        if auth_model is None:
            return self.ResponseModel(
                status=404,
                code="NOT_FOUND",
                message="The requested authorization does not exist!"
            )

        group_auth_models: Optional[List[GroupAuthorizationsModel]] = await database.group_authorizations. \
            retrieve_by_authorization_id(
            authorization_id=auth_model.id
        )

        if not group_auth_models:
            return self.ResponseModel(
                code="SUCCESS",
                status=200,
                groups=[]
            )

        group_models: List[GroupsModel] = await request.app.criadex.mysql_api.groups.retrieve_many_by_ids(
            *[model.group_id for model in group_auth_models]
        )

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            groups=group_models
        )


__all__ = ["view"]
