"""
HTTP client for Ragflow knowledge-base (dataset) and chat-assistant APIs.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

RAGFLOW_BASE_URL = os.getenv("RAGFLOW_URL", os.getenv("RAGFLOW_BASE_URL", "http://ragflow:9380")).rstrip("/")
RAGFLOW_KB_TIMEOUT_SECONDS = float(os.getenv("RAGFLOW_KB_TIMEOUT_SECONDS", "60"))
# Separate, longer timeout just for waiting on document parsing (parsing can take minutes).
RAGFLOW_PARSE_TIMEOUT_SECONDS = float(os.getenv("RAGFLOW_PARSE_TIMEOUT_SECONDS", "300"))


def kb_sync_enabled() -> bool:
    enabled = os.getenv("RAGFLOW_KB_SYNC_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    if not enabled:
        return False
    if not os.getenv("RAGFLOW_API_KEY", "").strip():
        return False
    return True


def _default_api_key() -> str:
    return os.getenv("RAGFLOW_API_KEY", "").strip()


class RagflowKbClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._base_url = (base_url or RAGFLOW_BASE_URL).rstrip("/")
        self._api_key = (api_key if api_key is not None else _default_api_key()).strip()
        self._timeout = timeout if timeout is not None else RAGFLOW_KB_TIMEOUT_SECONDS

    def _headers(self, json_body: bool = True) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        request_headers = self._headers(json_body=files is None)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_body,
                params=params,
                files=files,
                data=data,
            )
        try:
            payload = response.json()
        except Exception:
            response.raise_for_status()
            raise RuntimeError(f"Unexpected non-JSON response from Ragflow: {response.text[:500]}")

        if response.status_code >= 400:
            message = payload.get("message") if isinstance(payload, dict) else response.text
            raise RuntimeError(f"Ragflow HTTP {response.status_code}: {message}")

        if isinstance(payload, dict) and payload.get("code") not in (0, None):
            raise RuntimeError(f"Ragflow API error {payload.get('code')}: {payload.get('message')}")

        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected Ragflow response format")
        return payload

    @staticmethod
    def _missing_resource_error(exc: Exception, *, name_filter: bool) -> bool:
        """Ragflow uses 102/108 for missing or inaccessible filtered resources."""
        if not name_filter:
            return False
        message = str(exc).lower()
        return (
            "108" in message
            or "102" in message
            or "lacks permission" in message
            or "doesn't exist" in message
            or "does not exist" in message
            or "don't own" in message
            or "do not own" in message
        )

    @staticmethod
    def _already_gone_error(exc: Exception) -> bool:
        """True when the remote resource no longer exists — safe to ignore on delete."""
        message = str(exc).lower()
        return (
            "404" in message
            or "102" in message
            or "doesn't exist" in message
            or "does not exist" in message
            or "not found" in message
        )

    async def list_datasets(self, *, name: Optional[str] = None, dataset_id: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": 1, "page_size": 50}
        if name:
            params["name"] = name
        if dataset_id:
            params["id"] = dataset_id
        try:
            payload = await self._request("GET", "/api/v1/datasets", params=params)
        except RuntimeError as exc:
            if self._missing_resource_error(exc, name_filter=bool(name or dataset_id)):
                return []
            raise
        data = payload.get("data")
        if isinstance(data, list):
            return data
        return []

    async def create_dataset(
        self,
        *,
        name: str,
        description: str = "",
        embedding_model: Optional[str] = None,
        chunk_method: str = "naive",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name,
            "description": description,
            "permission": "me",
            "chunk_method": chunk_method,
        }
        if embedding_model:
            body["embedding_model"] = embedding_model
        payload = await self._request("POST", "/api/v1/datasets", json_body=body)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Ragflow create_dataset returned no data")
        return data

    async def delete_datasets(self, dataset_ids: list[str]) -> None:
        if not dataset_ids:
            return
        try:
            await self._request("DELETE", "/api/v1/datasets", json_body={"ids": dataset_ids})
        except RuntimeError as exc:
            if self._already_gone_error(exc):
                return
            raise

    async def list_documents(self, dataset_id: str, *, name: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": 1, "page_size": 100}
        if name:
            params["name"] = name
        try:
            payload = await self._request("GET", f"/api/v1/datasets/{dataset_id}/documents", params=params)
        except RuntimeError as exc:
            if self._missing_resource_error(exc, name_filter=bool(name)):
                return []
            raise
        data = payload.get("data")
        if isinstance(data, dict):
            docs = data.get("docs")
            if isinstance(docs, list):
                return docs
        if isinstance(data, list):
            return data
        return []

    async def upload_document(self, dataset_id: str, file_name: str, content: bytes) -> list[dict[str, Any]]:
        files = {"file": (file_name, content)}
        payload = await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents",
            files=files,
        )
        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []

    async def delete_documents(self, dataset_id: str, document_ids: list[str]) -> None:
        if not document_ids:
            return
        await self._request(
            "DELETE",
            f"/api/v1/datasets/{dataset_id}/documents",
            json_body={"ids": document_ids},
        )

    async def parse_documents(self, dataset_id: str, document_ids: list[str]) -> None:
        if not document_ids:
            return
        await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/chunks",
            json_body={"document_ids": document_ids},
        )

    async def list_chats(self, *, name: Optional[str] = None, chat_id: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": 1, "page_size": 50}
        if name:
            params["name"] = name
        if chat_id:
            params["id"] = chat_id
        try:
            payload = await self._request("GET", "/api/v1/chats", params=params)
        except RuntimeError as exc:
            if self._missing_resource_error(exc, name_filter=bool(name or chat_id)):
                return []
            raise
        data = payload.get("data")
        if isinstance(data, dict):
            chats = data.get("chats")
            if isinstance(chats, list):
                return chats
        if isinstance(data, list):
            return data
        return []

    async def wait_for_documents_parsed(
        self,
        dataset_id: str,
        document_ids: list[str],
        *,
        timeout: Optional[float] = None,
        poll_seconds: float = 2.0,
    ) -> bool:
        if not document_ids:
            return True

        # Use RAGFLOW_PARSE_TIMEOUT_SECONDS (default 300s) rather than the HTTP request
        # timeout so that large documents have enough time to be processed.
        effective_timeout = timeout if timeout is not None else RAGFLOW_PARSE_TIMEOUT_SECONDS
        deadline = time.monotonic() + effective_timeout
        pending = {str(doc_id) for doc_id in document_ids if doc_id}

        while time.monotonic() < deadline and pending:
            docs = await self.list_documents(dataset_id)
            by_id = {str(doc.get("id")): doc for doc in docs if doc.get("id")}
            done = {
                doc_id
                for doc_id in pending
                if str((by_id.get(doc_id) or {}).get("run", "")).upper() == "DONE"
            }
            pending -= done
            if not pending:
                return True
            await asyncio.sleep(poll_seconds)

        return not pending

    async def create_chat(
        self,
        *,
        name: str,
        dataset_ids: list[str],
        llm_id: Optional[str] = None,
        description: str = "Cria bot synced from Moodle",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name,
            "dataset_ids": dataset_ids,
            "description": description,
        }
        if llm_id:
            body["llm_id"] = llm_id
        payload = await self._request("POST", "/api/v1/chats", json_body=body)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Ragflow create_chat returned no data")
        return data

    async def patch_chat(self, chat_id: str, *, dataset_ids: list[str]) -> dict[str, Any]:
        # Ragflow uses PUT (not PATCH) for chat updates.
        payload = await self._request(
            "PUT",
            f"/api/v1/chats/{chat_id}",
            json_body={"dataset_ids": dataset_ids},
        )
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        return {}

    async def delete_chats(self, chat_ids: list[str]) -> None:
        if not chat_ids:
            return
        try:
            await self._request("DELETE", "/api/v1/chats", json_body={"ids": chat_ids})
        except RuntimeError as exc:
            if self._already_gone_error(exc):
                return
            raise
