from typing import List, Optional, Union

from fastapi import APIRouter, Body, Request
from pydantic import BaseModel, Field

from app.controllers.schemas import APIResponse, ERROR, GROUP_NOT_FOUND, INDEX_NOT_FOUND, SUCCESS
from criadex.index.schemas import Asset, IndexResponse, SearchConfig, TextNodeWithScore
from criadex.schemas import GroupNotFoundError, IndexNotFoundError

view = APIRouter()


class GraphBuildResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, ERROR]
    group_name: Optional[str] = None
    job_id: Optional[str] = None
    state: str = "QUEUED"
    source: str = "none"
    progress: int = 0
    error: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class GraphBuildJob(BaseModel):
    job_id: Optional[str] = None
    state: str = "QUEUED"
    source: str = "none"
    progress: int = 0
    error: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class GraphState(BaseModel):
    status: str = "NOT_BUILT"
    source: str = "none"
    node_count: int = 0
    edge_count: int = 0
    top_entities: List[str] = Field(default_factory=list)
    fallback_reason: Optional[str] = None
    error: Optional[str] = None
    built_at: Optional[int] = None
    updated_at: Optional[int] = None


class GraphStatusResponse(APIResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, ERROR]
    group_name: Optional[str] = None
    graph: GraphState = Field(default_factory=GraphState)
    job: Optional[GraphBuildJob] = None


class GraphSearchConfig(SearchConfig):
    max_hops: int = Field(default=1, ge=1, le=3)
    max_expansion_terms: int = Field(default=8, ge=0, le=30)
    auto_build: bool = False


class GraphSearchResponse(APIResponse, IndexResponse):
    code: Union[SUCCESS, GROUP_NOT_FOUND, INDEX_NOT_FOUND, ERROR]
    nodes: List[TextNodeWithScore] = Field(default_factory=list)
    assets: List[Asset] = Field(default_factory=list)
    search_units: int = 0
    graph_metadata: dict = Field(default_factory=dict)


@view.post(
    path="/groups/{group_name}/build_graph",
    name="Build Group Graph",
    summary="Build Group Graph",
    description="Builds a lightweight relationship graph for documents in the requested group.",
)
async def build_graph(group_name: str, request: Request) -> GraphBuildResponse:
    try:
        result = await request.app.criadex.build_graph(group_name=group_name)
        return GraphBuildResponse(
            code="SUCCESS",
            status=200,
            message=f"Successfully queued graph build for group '{group_name}'.",
            group_name=group_name,
            job_id=result.get("job_id"),
            state=result.get("state", "QUEUED"),
            source=result.get("source", "none"),
            progress=result.get("progress", 0),
            error=result.get("error"),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )
    except GroupNotFoundError:
        return GraphBuildResponse(
            code="GROUP_NOT_FOUND",
            status=404,
            message=f"The requested group '{group_name}' was not found!",
            group_name=group_name,
        )
    except Exception as ex:
        return GraphBuildResponse(
            code="ERROR",
            status=500,
            message=f"Failed to build graph: {str(ex)}",
            group_name=group_name,
        )


@view.get(
    path="/groups/{group_name}/graph_status",
    name="Get Group Graph Status",
    summary="Get Group Graph Status",
    description="Returns graph build status and summary metrics for the requested group.",
)
async def graph_status(group_name: str, request: Request) -> GraphStatusResponse:
    try:
        result = await request.app.criadex.graph_status(group_name=group_name)
        job_data = result.get("job")
        graph_data = result.get("graph", {})
        return GraphStatusResponse(
            code="SUCCESS",
            status=200,
            message=f"Successfully retrieved graph status for group '{group_name}'.",
            group_name=group_name,
            graph=GraphState(**graph_data),
            job=GraphBuildJob(
                job_id=job_data.get("job_id"),
                state=job_data.get("state", "QUEUED"),
                source=job_data.get("source", "none"),
                progress=job_data.get("progress", 0),
                error=job_data.get("error"),
                created_at=job_data.get("created_at"),
                updated_at=job_data.get("updated_at"),
            ) if isinstance(job_data, dict) else None,
        )
    except GroupNotFoundError:
        return GraphStatusResponse(
            code="GROUP_NOT_FOUND",
            status=404,
            message=f"The requested group '{group_name}' was not found!",
            group_name=group_name,
        )
    except Exception as ex:
        return GraphStatusResponse(
            code="ERROR",
            status=500,
            message=f"Failed to get graph status: {str(ex)}",
            group_name=group_name,
        )


@view.post(
    path="/groups/{group_name}/graph_search",
    name="Graph Search Group",
    summary="Graph Search Group",
    description="Runs group query with graph-based query expansion when graph is available.",
)
async def graph_search(
    group_name: str,
    request: Request,
    search_config: GraphSearchConfig = Body(...)
) -> GraphSearchResponse:
    try:
        index_response, graph_metadata = await request.app.criadex.graph_search(
            group_name=group_name,
            query=SearchConfig(**search_config.model_dump(exclude={"max_hops", "max_expansion_terms", "auto_build"})),
            max_hops=search_config.max_hops,
            max_expansion_terms=search_config.max_expansion_terms,
            auto_build=search_config.auto_build,
        )
        return GraphSearchResponse(
            code="SUCCESS",
            status=200,
            message=f"Successfully graph-queried group '{group_name}'.",
            nodes=index_response.nodes,
            assets=index_response.assets,
            search_units=index_response.search_units,
            graph_metadata=graph_metadata,
        )
    except GroupNotFoundError:
        return GraphSearchResponse(
            code="GROUP_NOT_FOUND",
            status=404,
            message=f"The requested group '{group_name}' was not found!",
        )
    except IndexNotFoundError as e:
        return GraphSearchResponse(
            code="INDEX_NOT_FOUND",
            status=404,
            message=str(e),
        )
    except Exception as ex:
        return GraphSearchResponse(
            code="ERROR",
            status=500,
            message=f"Failed to graph-query group: {str(ex)}",
        )


__all__ = ["view"]
