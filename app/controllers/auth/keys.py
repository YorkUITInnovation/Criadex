from typing import Optional, Union

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.auth.delete import AuthDeleteResponse
from app.controllers.schemas import catch_exceptions, SUCCESS, ERROR
from app.core.database.api import AuthDatabaseAPI
from app.core.database.tables.auth import AuthorizationsModel
from app.core.route import CriaRoute

view = APIRouter()


class AuthKeysResponse(AuthDeleteResponse):
    code: Union[SUCCESS, ERROR]
    authorized: Optional[bool] = None
    master: Optional[bool] = None


@cbv(view)
class CheckAuthKeysRoute(CriaRoute):
    ResponseModel = AuthKeysResponse

    @view.get(
        path="/auth/keys/{api_key}",
        name="Validate API Key (Keys Endpoint)",
        summary="Validate API Key (Keys Endpoint)",
        description="Check for an API key used to access this API. This endpoint is for compatibility with older clients.",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            api_key: str
    ) -> ResponseModel:
        database: AuthDatabaseAPI = request.app.auth
        auth_model: Optional[AuthorizationsModel] = await database.authorizations.retrieve(api_key)

        # Key DNE
        if auth_model is None:
            return self.ResponseModel(
                status=200,
                code="SUCCESS",
                api_key=api_key,
                master=False,
                authorized=False
            )

        # Key Exists
        return self.ResponseModel(
            status=200,
            code="SUCCESS",
            api_key=api_key,
            master=auth_model.master,
            authorized=True
        )


__all__ = ["view"]
