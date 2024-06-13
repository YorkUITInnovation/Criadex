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

from app.controllers.auth.delete import AuthDeleteResponse
from app.controllers.schemas import catch_exceptions, SUCCESS, ERROR
from app.core.database.api import AuthDatabaseAPI
from app.core.database.tables.auth import AuthorizationsModel
from app.core.route import CriaRoute

view = APIRouter()


class AuthCheckResponse(AuthDeleteResponse):
    code: Union[SUCCESS, ERROR]
    authorized: Optional[bool] = None
    master: Optional[bool] = None


@cbv(view)
class CheckAuthRoute(CriaRoute):
    ResponseModel = AuthCheckResponse

    @view.get(
        path="/auth/{api_key}/check",
        name="Validate API Key",
        summary="Validate API Key",
        description="Check for an API key used to access this API. Requires a master key.",
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
        auth_model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(api_key)

        # Key DNE
        if auth_model is None:
            return self.ResponseModel(
                status=200,
                code="SUCCESS",
                api_key=api_key,
                master=False,
                authorized=False
            )

        # Key Exists
        return self.ResponseModel(
            status=200,
            code="SUCCESS",
            api_key=api_key,
            master=auth_model.master,
            authorized=True
        )


__all__ = ["view"]
