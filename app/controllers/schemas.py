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

import logging
import time
import traceback
from functools import wraps
from typing import Optional, Type, Literal, TypeVar, Callable, Awaitable

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """
    Global API Response format that ALL responses must follow

    """

    status: int = 200
    message: Optional[str] = None
    timestamp: int = round(time.time())
    code: str = "SUCCESS"
    error: Optional[str] = Field(default=None, hidden=True)

    def dict(self, *args, **kwargs):

        self.message = self.message or {
            200: 'Request completed successfully!',
            409: 'The requested resource already exists!',
            400: 'You, the client, made a mistake...',
            500: 'An internal error occurred! :(',
            404: 'Womp womp. Not found!'
        }.get(self.status)

        data: dict = super().dict(*args, **kwargs)

        if data["error"] is None:
            del data["error"]

        return data

    class Config:
        @staticmethod
        def json_schema_extra(schema: dict, _):
            """Via https://github.com/tiangolo/fastapi/issues/1378"""
            props = {}
            for k, v in schema.get('properties', {}).items():
                if not v.get("hidden", False):
                    props[k] = v
            schema["properties"] = props


APIResponseModel = TypeVar('APIResponseModel', bound=APIResponse)


def catch_exceptions(
        output_shape: Type[APIResponse]
) -> Callable[..., Callable[..., Awaitable[APIResponseModel]]]:
    """
    Wrapper for controllers that handles exceptions & re-shapes them to match the response model

    :param output_shape:
    :return:
    """

    def error_handler(func):

        @wraps(func)
        async def wrapper(*args, **kwargs) -> APIResponseModel:
            try:
                return await func(*args, **kwargs)
            except Exception:
                logging.error(traceback.format_exc())
                return output_shape(
                    code="ERROR",
                    status=500,
                    message=f"An internal error occurred!",
                    error=traceback.format_exc()
                )

        return wrapper

    return error_handler


def exception_response(
        exception: Type[Exception],
        response: APIResponse,
        log_error: bool = False
) -> Callable[..., Callable[..., Awaitable[APIResponseModel]]]:
    """
    Wrapper for controllers that handles exceptions & re-shapes them to match the response model

    :param exception: The exception to statically handle
    :param response: The response
    :param log_error
    :return:
    """

    def error_handler(func):

        @wraps(func)
        async def wrapper(*args, **kwargs) -> APIResponseModel:
            try:
                return await func(*args, **kwargs)
            except exception:
                if log_error:
                    logging.getLogger("uvicorn.error").error(
                        "Caught Exception Response: " + traceback.format_exc()
                    )
                return response
        return wrapper

    return error_handler


UNAUTHORIZED: Type = Literal["UNAUTHORIZED"]
TIMEOUT: Type = Literal["TIMEOUT"]
ERROR: Type = Literal["ERROR"]
SUCCESS: Type = Literal["SUCCESS"]
NOT_FOUND: Type = Literal["NOT_FOUND"]
RATE_LIMIT: Type = Literal["RATE_LIMIT"]
DUPLICATE: Type = Literal["DUPLICATE"]
INVALID_FILE_TYPE: Type = Literal["INVALID_FILE_TYPE"]
INVALID_INDEX_TYPE: Type = Literal["INVALID_INDEX_TYPE"]
GROUP_NOT_FOUND: Type = Literal["GROUP_NOT_FOUND"]
FILE_NOT_FOUND: Type = Literal["FILE_NOT_FOUND"]
INVALID_FILE_DATA: Type = Literal["INVALID_FILE_DATA"]
MODEL_IN_USE: Type = Literal["MODEL_IN_USE"]
INVALID_MODEL: Type = Literal["INVALID_MODEL"]
INVALID_REQUEST: Type = Literal["INVALID_REQUEST"]
OPENAI_FILTER: Type = Literal["OPENAI_FILTER"]


class RateLimitResponse(APIResponse):
    status: int = 429
    code: RATE_LIMIT
