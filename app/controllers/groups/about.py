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

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, GROUP_NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.groups import GroupsModel
from criadex.schemas import GroupNotFoundError, IndexType, IndexTypeKeys

view = APIRouter()


class GroupsPublicModel(GroupsModel):
    type: IndexTypeKeys


class GroupAboutResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, ERROR]
    info: Optional[GroupsPublicModel] = None


@cbv(view)
class AboutGroupRoute(CriaRoute):
    ResponseModel = GroupAboutResponse

    @view.get(
        path="/groups/{group_name}/about",
        name="Get Group Info",
        summary="Get Group Info",
        description="Retrieve some basic info about the group.",
    )
    @catch_exceptions(
        ResponseModel
    )
    async def execute(
            self,
            request: Request,
            group_name: str
    ) -> ResponseModel:
        try:
            group_model: GroupsModel = await request.app.criadex.about(name=group_name)
        except GroupNotFoundError:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message=f"The requested index group '{group_name}' was not found!"
            )

        # Success!
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message=f"Successfully retrieved the group info for '{group_name}'.",
            info=GroupsPublicModel(
                **{
                    **group_model.dict(),
                    "type": IndexType(group_model.type).name
                }
            )
        )
