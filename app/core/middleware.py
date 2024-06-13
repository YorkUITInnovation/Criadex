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

import json

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class StatusMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):

        response: Response = await call_next(request)

        if response.headers.get('content-type') == 'application/json':
            return await self.handle_json_status(request, response)

        return response

    async def handle_json_status(self, request: Request, response: Response):
        binary = b''

        # noinspection PyUnresolvedReferences
        async for data in response.body_iterator:
            binary += data

        body: dict = json.loads(binary.decode())

        if "error" in body and not self.stack_trace_enabled(request):
            del body["error"]

        return JSONResponse(
            content=body,
            status_code=body.get('status', response.status_code)
        )

    @classmethod
    def stack_trace_enabled(cls, request: Request) -> bool:
        return request.headers.get("x-api-stacktrace", "") == "true"
