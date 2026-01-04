from fastapi.security import APIKeyQuery, APIKeyHeader

api_key_header: APIKeyQuery = APIKeyQuery(name="x-api-key", auto_error=False)
api_key_query: APIKeyHeader = APIKeyHeader(name="x-api-key", auto_error=False)

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

from typing import Union, List, Optional, Callable

from fastapi import Security, HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.controllers.schemas import APIResponse, UNAUTHORIZED
from criadex.schemas import UnauthorizedResponse
from app.core.database.tables.auth import AuthorizationsModel
from app.core.middleware import StatusMiddleware
from criadex.schemas import GroupNotFoundError


APP_API_KEYS: List[str] = []
handle_none_str: Callable = lambda key: None if key == "None" else key


class BadAPIKeyException(HTTPException):
    """
    Exception raised when an invalid API key is sent

    """


def unauthorized_exception_handler(request: Request, _exc: HTTPException) -> JSONResponse:
    """
    Handler for unauthorized exceptions

    :param request: Starlette request instance
    :param _exc: The exception
    :return: A JSONResponse matching the exception
    """

    submitted: str = (
            request.headers.get(api_key_header.model.name) or
            request.query_params.get(api_key_query.model.name)
    )

    return JSONResponse(
        status_code=401,
        content=UnauthorizedResponse(
            message=(
                f"Your key is unauthorized for this action."
                if submitted else
                "You did not send an API key, and are unauthorized for this action."
            ),
            detail=str(_exc.detail) if _exc.detail else None
        ).dict()
    )


async def get_api_key_master(
        request: Request,
        _api_key_query: str = Security(api_key_query),
        _api_key_header: str = Security(api_key_header)
) -> Union[str, JSONResponse]:
    """
    Check if an api key is a master key

    :param request: Starlette request object
    :param _api_key_query: API Key in query
    :param _api_key_header: API Key in header
    :return: API Key if authenticated
    :raises BadAPIKeyException: If API key does not have permission or is not provided

    """

    # Special-case: Allow /auth/{api_key}/check to proceed using the path param.
    # This endpoint validates an API key and should not require an additional header/query key.
    path: str = request.url.path or ""
    if path.startswith("/auth/") and path.endswith("/check"):
        try:
            return request.path_params.get("api_key")
        except Exception:
            pass

    # Special-case: Allow /group_auth/{group_name}/check to proceed using the api_key query param.
    # This endpoint allows any API key to check its own authorization without requiring a master key.
    if path.startswith("/group_auth/") and path.endswith("/check"):
        api_key_from_query = request.query_params.get("api_key")
        if api_key_from_query:
            # Validate that the API key exists (but don't require it to be master)
            auth_model = await request.app.auth.authorizations.retrieve(key=api_key_from_query)
            if auth_model is not None:
                # Return the API key to allow the endpoint to proceed
                return api_key_from_query

    # Special-case: Allow /group_auth/list to proceed using the api_key query param or header.
    # This endpoint allows any API key to list its own groups without requiring a master key.
    if path == "/group_auth/list":
        # Check query param first, then header (for flexibility)
        api_key_from_query = request.query_params.get("api_key")
        api_key_from_header = handle_none_str(_api_key_header) or handle_none_str(_api_key_query)
        api_key_to_check = api_key_from_query or api_key_from_header
        
        if api_key_to_check:
            # Validate that the API key exists (but don't require it to be master)
            auth_model = await request.app.auth.authorizations.retrieve(key=api_key_to_check)
            if auth_model is not None:
                # Return the API key to allow the endpoint to proceed
                return api_key_to_check

    api_key: str = handle_none_str(_api_key_header) or handle_none_str(_api_key_query)
    if api_key is None:
        raise BadAPIKeyException(status_code=401, detail="No API key was sent.")

    # Check if master
    if not await request.app.auth.authorizations.master(api_key):
        raise BadAPIKeyException(status_code=401, detail="Operation requires a master key, which this is not.")

    return api_key


async def check_group_auth(
        request: Request,
        api_key: str,
        group_names: List[str]
) -> Union[str, JSONResponse]:
    #############################################
    # FIRST WE CHECK IF THE KEY IS VALID AT ALL #
    #############################################

    if not group_names:
        return api_key

    # Database Key (Query)
    if api_key is None:
        raise BadAPIKeyException(status_code=401, detail="No API key was sent.")

    auth_model: Optional[AuthorizationsModel] = await request.app.auth.authorizations.retrieve(key=api_key)
    request.auth_model = auth_model

    if auth_model is None:
        raise BadAPIKeyException(status_code=401, detail="API key could not be found.")

    # Master bypasses all auth
    if auth_model.master:
        return api_key

    # ^ Since they are NOT master but trying to access stack trace, throw an error
    # It's a security concern to give stacktraces as it leaks implementation
    if StatusMiddleware.stack_trace_enabled(request):
        raise BadAPIKeyException(status_code=401, detail="Only master keys can access stacktraces!")

    ###################################################
    # NOW WE CHECK IF THE KEY HAS ACCESS TO THE INDEX GROUP #
    ###################################################

    for group_name in group_names:
        index_id: Optional[int] = await request.app.criadex.get_id(name=group_name, throw_not_found=False)

        if index_id is None:
            raise GroupNotFoundError(f"The group '{group_name}' was not found!")

        # If it is registered, let's run a check
        if not await request.app.auth.group_authorizations.exists(group_id=index_id, authorization_id=auth_model.id):
            raise BadAPIKeyException(status_code=401, detail=f"Your key is not authorized on the '{group_name}' index.")

    # All good to go!
    return api_key


async def get_api_key_group(
        request: Request,
        _api_key_query: Optional[str] = Security(api_key_query),
        _api_key_header: Optional[str] = Security(api_key_header)
) -> Union[str, JSONResponse]:
    """
    Check if an api key has access to an index

    :param request: Starlette request object
    :param _api_key_query: API Key in query
    :param _api_key_header: API Key in header
    :return: API Key if authenticated
    :raises BadAPIKeyException: If API key does not have permission or is not provided

    """

    api_key: str = handle_none_str(_api_key_header) or handle_none_str(_api_key_query)
    # Allow using the explicit 'api_key' query param for the group check endpoint
    path: str = request.url.path or ""
    if (api_key is None) and path.startswith("/group_auth/") and path.endswith("/check"):
        api_key = request.query_params.get("api_key")

    try:
        group_names: List[str] = [request.path_params['group_name']]
        result = await check_group_auth(request, api_key, group_names)
    except GroupNotFoundError:
        return api_key
    except KeyError:
        raise BadAPIKeyException(status_code=500, detail="No API key was found in the query.")

    return result


async def get_api_key_model_query(
        request: Request,
        _api_key_query: Optional[str] = Security(api_key_query),
        _api_key_header: Optional[str] = Security(api_key_header)
) -> Union[str, JSONResponse]:
    """
    Check if an api key has access to query a model

    :param request: Starlette request object
    :param _api_key_query: API Key in query
    :param _api_key_header: API Key in header
    :return: API Key if authenticated
    :raises BadAPIKeyException: If API key does not have permission or is not provided

    """

    #############################################
    # FIRST WE CHECK IF THE KEY IS VALID AT ALL #
    #############################################

    # Database Key
    api_key: str = handle_none_str(_api_key_header) or handle_none_str(_api_key_query)
    if api_key is None:
        raise BadAPIKeyException(status_code=401, detail="")

    auth_model: Optional[AuthorizationsModel] = await request.app.auth.authorizations.retrieve(key=api_key)

    if auth_model is None:
        raise BadAPIKeyException(status_code=401)

    # Master bypasses all auth
    if auth_model.master:
        return api_key

    # ^ Since they are NOT master but trying to access stack trace, throw an error
    # It's a security concern to give stacktraces as it leaks implementation
    if StatusMiddleware.stack_trace_enabled(request):
        raise BadAPIKeyException(status_code=401, detail="Only master keys can access stacktraces!")

    ###################################################
    # NOW WE CHECK IF THE KEY HAS ACCESS TO THE MODEL #
    ###################################################

    model_id: Optional[str] = request.path_params.get('model_id', None)

    # Should never be thrown, but just in case...
    if not model_id:
        raise BadAPIKeyException(status_code=401, detail="No API key was sent.")

    # If the model doesn't exist, let it be handled as a 404
    if not await request.app.criadex.exists_azure_model(model_id=model_id):
        return api_key

    # Check for access
    has_access: bool = await request.app.auth.group_authorizations.has_llm_access(
        authorization_id=auth_model.id,
        llm_model_id=model_id
    )

    # If they don't have access, throw a 401
    if not has_access:
        raise BadAPIKeyException(status_code=401, detail="Your key does not have access to the selected model.")

    # All good to go!
    return api_key



