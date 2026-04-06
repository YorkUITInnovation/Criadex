import os
from typing import Any, Dict, Optional

import httpx


class RagflowGraphRAGClient:
    def __init__(self):
        self._build_url_template = os.getenv(
            "RAGFLOW_GRAPH_BUILD_URL_TEMPLATE",
            "http://ragflow:80/api/v1/datasets/{group_name}/graph/build"
        )
        self._status_url_template = os.getenv(
            "RAGFLOW_GRAPH_STATUS_URL_TEMPLATE",
            "http://ragflow:80/api/v1/datasets/{group_name}/graph/status"
        )
        self._search_url_template = os.getenv(
            "RAGFLOW_GRAPH_SEARCH_URL_TEMPLATE",
            "http://ragflow:80/api/v1/datasets/{group_name}/graph/search"
        )
        self._timeout = float(os.getenv("RAGFLOW_GRAPH_TIMEOUT_SECONDS", "20"))
        self._api_key = os.getenv("RAGFLOW_API_KEY")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-API-Key"] = self._api_key
        return headers

    async def _request(self, method: str, url: str, payload: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                json=payload,
                headers=self._headers()
            )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError("Unexpected RAGFlow response format")
        return result

    async def build_graph(self, group_name: str) -> Dict[str, Any]:
        url = self._build_url_template.format(group_name=group_name)
        payload = {"dataset_id": group_name}
        return await self._request("POST", url, payload=payload)

    async def graph_status(self, group_name: str) -> Dict[str, Any]:
        url = self._status_url_template.format(group_name=group_name)
        return await self._request("GET", url)

    async def graph_search(
        self,
        group_name: str,
        query: str,
        max_hops: int,
        max_expansion_terms: int
    ) -> Dict[str, Any]:
        url = self._search_url_template.format(group_name=group_name)
        payload = {
            "query": query,
            "max_hops": max_hops,
            "max_expansion_terms": max_expansion_terms,
        }
        return await self._request("POST", url, payload=payload)
