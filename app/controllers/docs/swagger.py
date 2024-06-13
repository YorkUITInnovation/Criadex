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

from typing import Annotated

import typing_extensions
from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.controllers.schemas import catch_exceptions, APIResponse
from app.controllers.security import api_key_header, api_key_query
from app.core import config
from app.core.route import CriaRoute

view = APIRouter()

Doc = getattr(typing_extensions, "Doc")


def get_custom_swagger_ui_html(
        *,
        openapi_url: Annotated[
            str,
            Doc(
                """
                The OpenAPI URL that Swagger UI should load and use.
    
                This is normally done automatically by FastAPI using the default URL
                `/openapi.json`.
                """
            ),
        ],
        title: Annotated[
            str,
            Doc(
                """
                The HTML `<title>` content, normally shown in the browser tab.
                """
            ),
        ],
        swagger_js_url: Annotated[
            str,
            Doc(
                """
                The URL to use to load the Swagger UI JavaScript.
    
                It is normally set to a CDN URL.
                """
            ),
        ] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url: Annotated[
            str,
            Doc(
                """
                The URL to use to load the Swagger UI CSS.
    
                It is normally set to a CDN URL.
                """
            ),
        ] = "https://unpkg.com/swagger-ui-dist/swagger-ui.css",
        swagger_favicon_url: Annotated[
            str,
            Doc(
                """
                The URL of the favicon to use. It is normally shown in the browser tab.
                """
            ),
        ] = "https://fastapi.tiangolo.com/img/favicon.png"
) -> HTMLResponse:
    html = """
    <!doctype html>
    <html>
      <head>
        <link rel="shortcut icon" href="%swagger_favicon_url%">
        <title>%title%</title>
        <script src="%swagger_js_url%"></script>
        
        <!-- Load Swagger UI -->
        <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script> 
    
        <!-- Load the HierarchicalTags Plugin -->
        <script src="https://unpkg.com/swagger-ui-plugin-hierarchical-tags"></script>
    
        <!-- Load styles -->
        <link rel="stylesheet" type="text/css" href="%swagger-css%" />
    
        <script>
          window.onload = function() {
            SwaggerUIBundle({
              url: "%openapi-url%",
              dom_id: "#swagger",
              plugins: [
                HierarchicalTagsPlugin
              ],
              hierarchicalTagSeparator: /[:|]/
            })
          }
        </script>
      </head>
      <body>
        <div id="swagger"></div>
      </body>
    </html> 
    """

    html = html \
        .replace("%openapi-url%", openapi_url) \
        .replace("%swagger-css%", swagger_css_url) \
        .replace("%swagger_favicon_url%", swagger_favicon_url) \
        .replace("%title%", title) \
        .replace("%swagger_js_url%", swagger_js_url)

    return HTMLResponse(html)


@cbv(view)
class DocsRedirectRoute(CriaRoute):
    ResponseModel = HTMLResponse

    @view.get(
        "/docs",
    )
    @catch_exceptions(
        APIResponse
    )
    async def execute(
            self,
            request: Request,
            dark_enabled: int = 1
    ) -> ResponseModel:
        kwargs = {}

        api_key: str = (
                request.headers.get(api_key_header.model.name) or
                request.query_params.get(api_key_query.model.name)
        )

        api_key_arg = f"?{api_key_query.model.name}={api_key}"

        if dark_enabled:
            kwargs["swagger_css_url"] = f"/styles" + api_key_arg

        return get_custom_swagger_ui_html(
            openapi_url="/openapi.json" + api_key_arg,
            title=config.SWAGGER_TITLE,
            swagger_favicon_url=config.SWAGGER_FAVICON,
            **kwargs
        )


__all__ = ["view"]
