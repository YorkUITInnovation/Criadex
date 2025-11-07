from typing import Optional, List, Union
from fastapi import APIRouter, Body, Request
from fastapi_utils.cbv import cbv
from app.controllers.schemas import APIResponse, SUCCESS, ERROR, GROUP_NOT_FOUND
from app.core.route import CriaRoute
from criadex.schemas import GroupNotFoundError
from criadex.index.schemas import SearchConfig, IndexResponse, TextNodeWithScore, Asset

view = APIRouter()


class GroupQueryResponse(APIResponse, IndexResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, ERROR]


@cbv(view)
class QueryGroupRoute(CriaRoute):
    ResponseModel = GroupQueryResponse
    
    @view.post(
        path="/groups/{group_name}/query",
        name="Query Group",
        summary="Query a specific group (knowledge base).",
        description="Sends a query to the specified group and retrieves relevant information.",
    )
    async def execute(
            self,
            group_name: str,
            request: Request,
            search_config: SearchConfig = Body(...),
    ) -> ResponseModel:
        try:
            results_index_response: IndexResponse = await request.app.criadex.search(group_name=group_name, query=search_config)

            return self.ResponseModel(
                code="SUCCESS",
                status=200,
                message=f"Successfully queried group '{group_name}'.",
                nodes=results_index_response.nodes,
                assets=results_index_response.assets,
                search_units=results_index_response.search_units
            )
        except GroupNotFoundError:
            return self.ResponseModel(
                code="GROUP_NOT_FOUND",
                status=404,
                message=f"The requested group '{group_name}' was not found!",
                nodes=[],
                assets=[],
                search_units=0
            )
        except Exception as e:
            return self.ResponseModel(
                code="ERROR",
                status=500,
                message=f"An internal error occurred: {str(e)}",
                nodes=[],
                assets=[],
                search_units=0
            )