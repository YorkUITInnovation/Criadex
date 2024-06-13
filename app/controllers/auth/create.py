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
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.auth.delete import AuthDeleteResponse
from app.controllers.schemas import catch_exceptions, SUCCESS, DUPLICATE, ERROR
from app.core.database.api import AuthDatabaseAPI
from app.core.database.tables.auth import AuthorizationsModel
from app.core.route import CriaRoute

view = APIRouter()


class AuthKeyConfig(BaseModel):
    master: bool


class AuthCreateResponse(AuthDeleteResponse):
    code: Union[SUCCESS, DUPLICATE, ERROR]
    master: Optional[bool] = None


@cbv(view)
class CreateAuthRoute(CriaRoute):
    ResponseModel = AuthCreateResponse

    @view.post(
        path="/auth/{api_key}/create",
        name="Create API Key",
        summary="Create API Key",
        description="Create an API key to access this API. Requires a master key.",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            api_key: str,
            key_config: AuthKeyConfig
    ) -> ResponseModel:
        # Retrieve
        database: AuthDatabaseAPI = request.app.auth
        model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(api_key)

        # If exists, it's a duplicate
        if model is not None:
            return self.ResponseModel(
                status=409,
                code="DUPLICATE",
                message="Duplicate key..."
            )

        # Insert into database
        await database.authorizations.insert(
            key=api_key,
            master=int(key_config.master)
        )

        # Success!
        return self.ResponseModel(
            status=200,
            code="SUCCESS",
            api_key=api_key,
            master=key_config.master
        )


__all__ = ["view"]
