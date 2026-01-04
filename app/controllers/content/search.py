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

from fastapi import APIRouter, Security
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, exception_response, APIResponse, SUCCESS, GROUP_NOT_FOUND, \
    INVALID_REQUEST, ERROR, UNAUTHORIZED
from app.core.security import check_group_auth, api_key_query, api_key_header, \
    handle_none_str, BadAPIKeyException
from app.core.config import SEARCH_INDEX_LIMIT_DAY, SEARCH_INDEX_LIMIT_HOUR, SEARCH_INDEX_LIMIT_MINUTE
from app.core.route import CriaRoute
from app.core.schemas import index_search_limiter
from criadex.group import Group

# Legacy import removed. Define locally:
class EmptyPromptError(Exception):
    pass
from criadex.index.schemas import IndexResponse, SearchConfig
from criadex.schemas import GroupNotFoundError

view = APIRouter()


class ContentSearchResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, INVALID_REQUEST, UNAUTHORIZED, ERROR]
    response: Optional[IndexResponse] = None


@cbv(view)
class SearchContentRoute(CriaRoute):
    ResponseModel = ContentSearchResponse

    @view.post(
        path="/groups/{group_name}/content/search",
        name="Search an Index",
        summary="Search an Index",
        description="Search an index for some vectorized nodes.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        EmptyPromptError,
        ResponseModel(
            code="INVALID_REQUEST",
            status=400,
            message="The prompt supplied was empty."
        )
    )
    @index_search_limiter.limit(SEARCH_INDEX_LIMIT_DAY)
    @index_search_limiter.limit(SEARCH_INDEX_LIMIT_HOUR)
    @index_search_limiter.limit(SEARCH_INDEX_LIMIT_MINUTE)
    async def execute(
            self,
            request: Request,
            group_name: str,
            config: SearchConfig,
            _api_key_query: Optional[str] = Security(api_key_query),
            _api_key_header: Optional[str] = Security(api_key_header),
    ) -> ResponseModel:

        # Grab the group
        try:
            group: Group = await request.app.criadex.get(name=group_name)
        except GroupNotFoundError:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message=f"The requested index group '{group_name}' was not found!"
            )

        # Must perform extra auth for the extra_groups parameter
        api_key: str = handle_none_str(_api_key_header) or handle_none_str(_api_key_query)

        try:
            await check_group_auth(request, api_key=api_key, group_names=config.extra_groups or [])
        except BadAPIKeyException as ex:
            return self.ResponseModel(
                code="UNAUTHORIZED",
                status=401,
                message=ex.detail
            )

        # Now search
        response: IndexResponse = await group.search(group_name, config)

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully retrieved searched the index for the requested content.",
            response=response
        )


__all__ = ["view"]
