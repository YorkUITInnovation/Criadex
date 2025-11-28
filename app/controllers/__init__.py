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
from typing import Optional, Literal

from fastapi import APIRouter, Header, Depends
from starlette.responses import Response

from app.controllers import agents, docs, auth, content, group_auth, models, groups, ragflow
from app.controllers.models import cohere_models, azure_models


# noinspection PyPep8Naming
def custom_headers(X_Api_Stacktrace: bool = Header(default=False)) -> bool:
    return X_Api_Stacktrace


router = APIRouter(dependencies=[Depends(custom_headers)])

router.include_router(auth.router)
router.include_router(docs.router)
router.include_router(group_auth.router)
router.include_router(groups.router)
router.include_router(content.router)
router.include_router(models.router)
router.include_router(agents.router)
router.include_router(ragflow.view)


class HealthCheckFilter(logging.Filter):
    HEALTH_ENDPOINT: str = "/health_check"

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self.HEALTH_ENDPOINT) == -1


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@router.get(HealthCheckFilter.HEALTH_ENDPOINT, include_in_schema=False)
async def health_check() -> Response:
    """
    Check if the server is online (for docker health check)
    :return: Just a simple 200

    """

    return Response(status_code=200, content="Pong!")


__all__ = ["router"]
