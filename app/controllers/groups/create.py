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

from typing import Union, Optional

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, DUPLICATE, INVALID_MODEL, \
    ERROR
from app.core.route import CriaRoute
from criadex.criadex import Criadex
from criadex.schemas import GroupConfig, GroupExistsError, PartialGroupConfig

view = APIRouter()


class GroupCreateResponse(APIResponse):
    code: Union[SUCCESS, DUPLICATE, INVALID_MODEL, ERROR]
    config: Optional[GroupConfig] = None


@cbv(view)
class CreateGroupRoute(CriaRoute):
    ResponseModel = GroupCreateResponse

    @view.post(
        path="/groups/{group_name}/create",
        name="Create a Group",
        summary="Create a Group",
        description="Create an group on the Criadex indexing server.",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            group_name: str,
            group_config: PartialGroupConfig
    ) -> ResponseModel:
        config: GroupConfig = GroupConfig(**group_config.dict(), **{"name": group_name})
        criadex: Criadex = request.app.criadex

        # Confirm the LLM model exists!
        if not await criadex.exists_azure_model(model_id=config.llm_model_id):
            return self.ResponseModel(
                code="INVALID_MODEL",
                status=400,
                message="The specified LLM model is invalid and does not exist in the database!",
                config=config
            )

        # Confirm the Embedding model exists!
        if not await criadex.exists_azure_model(model_id=config.embedding_model_id):
            return self.ResponseModel(
                code="INVALID_MODEL",
                status=400,
                message="The specified embedding model is invalid and does not exist in the database!",
                config=config
            )

        # Try to create it
        try:
            await criadex.create(config=config)
        except GroupExistsError:
            return self.ResponseModel(
                code="DUPLICATE",
                status=409,
                message=f"The requested group '{config.name}' already exists!",
                config=config
            )

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully created the group.",
            config=config
        )
