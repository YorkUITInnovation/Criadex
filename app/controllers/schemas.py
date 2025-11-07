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
from criadex.schemas import APIResponse, APIResponseModel, UNAUTHORIZED, TIMEOUT, ERROR, SUCCESS, NOT_FOUND, RATE_LIMIT, DUPLICATE, INVALID_INDEX_TYPE, GROUP_NOT_FOUND, FILE_NOT_FOUND, INVALID_FILE_DATA, MODEL_IN_USE, INVALID_MODEL, INVALID_REQUEST, OPENAI_FILTER, RateLimitResponse, GroupExistsResponse, MODEL_NOT_FOUND


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