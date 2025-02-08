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

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from pydantic import ValidationError
from starlette.requests import Request

from app.controllers.content.upload import ContentUploadResponse, ContentUploadConfig
from app.controllers.schemas import catch_exceptions, exception_response, SUCCESS, \
    GROUP_NOT_FOUND, INVALID_FILE_DATA, FILE_NOT_FOUND, ERROR
from app.core.route import CriaRoute
from criadex.group import Group
from criadex.index.schemas import Bundle, BundleConfig
from criadex.schemas import GroupNotFoundError, DocumentNotFoundError

view = APIRouter()


class ContentUpdateResponse(ContentUploadResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, INVALID_FILE_DATA, FILE_NOT_FOUND, ERROR]
    token_usage: Optional[int] = None


@cbv(view)
class UpdateContentRoute(CriaRoute):
    ResponseModel = ContentUpdateResponse

    @view.patch(
        path="/groups/{group_name}/content/update",
        name="Update Index Content",
        summary="Update Index Content",
        description="Update file content already on the API. Data sent will be re-indexed & stored.",
    )
    @catch_exceptions(
        ResponseModel
    )
    @exception_response(
        DocumentNotFoundError,
        ResponseModel(
            code="FILE_NOT_FOUND",
            status=404,
            message="Requested content does not exist in the database."
        )
    )
    async def execute(
            self,
            request: Request,
            group_name: str,
            file: ContentUploadConfig
    ) -> ResponseModel:

        # Get the group
        try:
            group: Group = await request.app.criadex.get(group_name)
        except GroupNotFoundError:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message=f"The requested index group '{group_name}' was not found"
            )

        # Convert the file
        try:
            bundle: Bundle[BundleConfig] = await group.index.convert(
                group_model=await request.app.criadex.get_model(group_name=group_name),
                file=file
            )
        except ValidationError as ex:
            return self.ResponseModel(
                code="INVALID_FILE_DATA",
                status=400,
                message=(
                        f"File data invalid. Does not match the required struct for this index type:\n"
                        + ex.json()
                )
            )

        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully updated & re-indexed the content.",
            token_usage=await request.app.criadex.update_file(group=group, bundle=bundle)
        )


__all__ = ["view"]
