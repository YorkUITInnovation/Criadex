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

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, NOT_FOUND, ERROR
from app.core.database.api import AuthDatabaseAPI
from app.core.database.tables.auth import AuthorizationsModel
from app.core.route import CriaRoute

view = APIRouter()


class AuthDeleteResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]
    api_key: Optional[str] = None


@cbv(view)
class DeleteAuthRoute(CriaRoute):
    ResponseModel = AuthDeleteResponse

    @view.delete(
        path="/auth/{api_key}/delete",
        name="Delete API Key",
        summary="Delete API Key",
        description="Delete an API key used to access this API. Requires a master key.",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            api_key: str
    ) -> ResponseModel:
        database: AuthDatabaseAPI = request.app.auth
        model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(api_key)

        if model is None:
            return self.ResponseModel(
                status=400,
                code="NOT_FOUND",
                message="That key was not found."
            )

        # First delete any index authorizations
        await database.group_authorizations.delete_all_by_authorization_id(authorization_id=model.id)

        # Now delete the auth
        await database.authorizations.delete(key=model.key)

        return AuthDeleteResponse(
            status=200,
            code="SUCCESS",
            api_key=model.key
        )


__all__ = ["view"]
