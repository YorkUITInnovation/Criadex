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


class AuthResetResponse(APIResponse):
    code: Union[SUCCESS, NOT_FOUND, ERROR]
    new_key: Optional[str] = None


@cbv(view)
class ResetAuthRoute(CriaRoute):
    ResponseModel = AuthResetResponse

    @view.patch(
        path="/auth/{api_key}/reset",
        name="Reset API Key",
        summary="Reset API Key",
        description="Reset the token for an API key without remaking it. Requires a master key.",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            api_key: str,
            new_key: str
    ) -> ResponseModel:
        # Retrieve
        database: AuthDatabaseAPI = request.app.auth
        auth_model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(api_key)

        # If it does not exist, that's an issue
        if auth_model is None:
            return self.ResponseModel(
                status=400,
                code="NOT_FOUND",
                message="That key was not found"
            )

        # Update value
        await database.authorizations.reset(
            key=api_key,
            new_key=new_key
        )

        # Success!
        return self.ResponseModel(
            status=200,
            code="SUCCESS",
            new_key=new_key
        )


__all__ = ["view"]
