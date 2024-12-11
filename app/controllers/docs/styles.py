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

from pathlib import Path

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.responses import Response

from app.controllers.schemas import catch_exceptions, APIResponse
from app.core import config
from app.core.route import CriaRoute
from app.core.schemas import AppMode

view = APIRouter()


@cbv(view)
class DocsRedirectRoute(CriaRoute):
    ResponseModel = Response
    CSS_FP: Path = Path(__file__).parent.joinpath("theme.css")
    CSS: str = open(CSS_FP, "r").read()

    def get_css(self) -> str:
        """Get CSS for theme"""

        if config.APP_MODE == AppMode.PRODUCTION:
            return self.CSS
        return open(self.CSS_FP, "r").read()

    @view.get(
        "/styles",
    )
    @catch_exceptions(
        APIResponse
    )
    async def execute(self) -> ResponseModel:
        return Response(
            content=self.get_css(),
            headers={"Content-Type": "text/css"}
        )


__all__ = ["view"]
