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

from typing import Optional

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import State
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.controllers.__init__ import router
from app.core.security import BadAPIKeyException, unauthorized_exception_handler
from criadex.criadex import Criadex
from . import config
from .database.api import AuthDatabaseAPI
from .middleware import StatusMiddleware
from .schemas import index_search_limiter, model_query_limiter, AppMode
from ..controllers.schemas import RateLimitResponse


import os
import logging
import warnings
from typing import List, Optional, Any
from contextlib import asynccontextmanager

class CriadexAPI(FastAPI):
    """
    FastAPI server
    """

    ORIGINS: List[str] = [os.environ.get("APP_API_ORIGINS", "*")]

    def __init__(
        self,
        criadex: Criadex,
        **extra: Any
    ):
        super().__init__(**extra)

        # FastAPI Setup
        self.state = getattr(self, 'state', State())
        self.logger = logging.getLogger('uvicorn.info')

        # Criadex Setup
        self.criadex = criadex
        self.auth = None

    @classmethod
    def create(
        cls,
        criadex: Optional[Criadex] = None,
    ):
        """
        :return: Instance of the FastAPI app
        """
        if config.APP_MODE == AppMode.TESTING:
            mysql_creds = config.MYSQL_CREDENTIALS.model_copy()
            mysql_creds.host = '127.0.0.1'
            mysql_creds.database = 'criadex_test'
        else:
            mysql_creds = config.MYSQL_CREDENTIALS

        _app = CriadexAPI(
            criadex=criadex or Criadex(
                mysql_credentials=mysql_creds,
                elasticsearch_credentials=config.ELASTICSEARCH_CREDENTIALS
            ),
            docs_url=None,
            openapi_url=None,
            lifespan=cls.app_lifespan
        )

        # Add extra bells & whistles
        _app.include_router(router)
        _app.include_handlers()
        _app.include_middlewares()

        # Please shut up
        logging.getLogger('asyncio').setLevel(logging.CRITICAL)
        warnings.filterwarnings('ignore', module='aiomysql')

        return _app

    def include_handlers(self) -> None:
        """
        Include API handlers

        :return: None

        """

        self.add_exception_handler(RateLimitExceeded, self.rate_limit_handler)
        self.add_exception_handler(BadAPIKeyException, unauthorized_exception_handler)
        self.state.index_search_limiter = index_search_limiter
        self.state.model_query_limiter = model_query_limiter

    def include_middlewares(self) -> None:
        """
        Include CORS handling

        :return: None

        """

        self.add_middleware(
            CORSMiddleware,
            allow_origins=CriadexAPI.ORIGINS,
            allow_credentials=True,
            allow_methods=CriadexAPI.ORIGINS,
            allow_headers=CriadexAPI.ORIGINS,
        )

        self.add_middleware(
            StatusMiddleware
        )

    @classmethod
    def rate_limit_handler(cls, request: Request, _: RateLimitExceeded) -> JSONResponse:
        """
        Build a simple JSON response that includes the details of the rate limit
        that was hit. If no limit is hit, the countdown is added to headers.

        :param request: The request
        :param _: The error
        :return: The response

        """

        # Still replies in the correct APIResponse format
        response: JSONResponse = JSONResponse(
            content=RateLimitResponse(
                message="You hit the rate limit for this (to prevent accidents or abuse costing $20,000 in a day)"
            ).json(),
            status_code=429
        )

        # noinspection PyProtectedMember
        return request.app.state.index_search_limiter._inject_headers(response, request.state.view_rate_limit)

    async def preflight_checks(self) -> bool:
        """
        Run preflight checks to confirm app is ready to "fly"

        :return: Whether to kill the app startup

        """

        preflight_failed: bool = False

        # Check if in docker
        if os.environ.get('IN_DOCKER'):
            self.logger.info("Application loaded within a Docker container.")

        # Check if .env files loaded
        if config.ENV_LOADED:
            self.logger.info("Loaded '.env' configuration file with environment variables.")

        # Check if successful
        if preflight_failed:
            self.logger.error('Application failed preflight checks and will not be able to run.')
            return False

        return True

    @staticmethod
    @asynccontextmanager
    async def app_lifespan(criadex_api):
        """
        Handle the lifespan of the app

        :return: Context manager for Criadex

        """

        # Preflight Checks
        if not await criadex_api.preflight_checks():
            exit()

        # Initialization
        await criadex_api._initialize(criadex_api)

        # Shutdown is after yield
        yield

        criadex_api.logger.info("Shutting down Criadex...")

    @classmethod
    async def _initialize(
            cls,
            criadex_api
    ):
        await criadex_api.criadex.initialize()
        criadex_api.auth = AuthDatabaseAPI(pool=criadex_api.criadex.mysql_api.pool)
        await criadex_api.auth.initialize()

