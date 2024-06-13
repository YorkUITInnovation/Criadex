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
import os
from enum import Enum
from json import JSONDecodeError
from typing import Optional

from fastapi import Form
from slowapi import Limiter
from starlette import status
from starlette.exceptions import HTTPException

from app.controllers.schemas import APIResponse, RATE_LIMIT

"""Create a rate limiter for the index group search function to prevent abuse"""
index_search_limiter: Limiter = Limiter(key_func=lambda request: request.path_params.get('index_name'))

"""Create a rate limiter for the model use function to prevent abuse"""
model_query_limiter: Limiter = Limiter(key_func=lambda request: request.path_params.get('model_id'))


class AppMode(Enum):
    """
    Whether the app is loaded in production or not

    """

    TESTING = 1
    PRODUCTION = 2


class EnvNotFoundException(FileNotFoundError):
    """Raised when the .env file cannot be found"""


def check_env_path(env_path: str) -> str:
    """
    Check if the dotenv file exists. If it doesn't, throw an error.

    :param env_path: The .env path
    :return: The path that we received originally

    """

    if not os.path.isfile(env_path):
        raise EnvNotFoundException(
            f"Failed to locate dotenv file at '{env_path}'. "
            f"Specify location with the ENV_PATH environment variable"
        )

    return env_path


class RateLimitResponse(APIResponse):
    status: int = 429
    code: RATE_LIMIT

