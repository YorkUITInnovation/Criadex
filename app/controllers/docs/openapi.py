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

from fastapi import APIRouter
from fastapi.openapi.utils import get_openapi
from fastapi_utils.cbv import cbv
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.controllers.schemas import catch_exceptions, APIResponse
from app.core import config
from app.core.route import CriaRoute

view = APIRouter()


@cbv(view)
class OpenAPIRoute(CriaRoute):
    ResponseModel = JSONResponse

    @view.get(
        "/openapi.json",
        response_class=JSONResponse
    )
    @catch_exceptions(APIResponse)
    async def execute(self, request: Request) -> ResponseModel:
        openapi_schema = get_openapi(
            title=config.APP_TITLE,
            version=config.APP_VERSION,
            description=config.SWAGGER_DESCRIPTION,
            routes=request.app.routes,
        )

        return JSONResponse(content=openapi_schema)


__all__ = ["view"]
