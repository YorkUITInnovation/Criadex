"""
Ragflow knowledge-base and chat facade backed by the native ragflow-sdk.

Replaces the hand-written httpx boundary with the InfiniFlow ragflow_sdk
(v0.26.x). The public RagflowKbClient interface is unchanged so kb_sync.py
and its callers need no modifications.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Optional

import requests
from ragflow_sdk import RAGFlow
from ragflow_sdk.modules.chat import Chat
from ragflow_sdk.modules.dataset import DataSet
from ragflow_sdk.modules.document import Document

logger = logging.getLogger(__name__)

RAGFLOW_BASE_URL = os.getenv("RAGFLOW_URL", os.getenv("RAGFLOW_BASE_URL", "http://ragflow:9380")).rstrip("/")
RAGFLOW_KB_TIMEOUT_SECONDS = float(os.getenv("RAGFLOW_KB_TIMEOUT_SECONDS", "60"))
# Separate, longer timeout for waiting on document parsing (parsing can take minutes).
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


class _TimedRAGFlow(RAGFlow):
    """RAGFlow subclass that enforces per-request timeouts on all HTTP verbs.

    Uses a shared requests.Session per instance so TCP connections are reused
    across SDK calls (keep-alive) rather than reconnecting on every request.
    """

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        super().__init__(api_key, base_url)
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(self.authorization_header)

    def post(self, path, json=None, stream=False, files=None):
        return self._session.post(
            url=self.api_url + path,
            json=json,
            stream=stream,
            files=files,
            timeout=self._timeout,
        )

    def get(self, path, params=None, json=None):
        return self._session.get(
            url=self.api_url + path,
            params=params,
            json=json,
            timeout=self._timeout,
        )

    def delete(self, path, json):
        return self._session.delete(
            url=self.api_url + path,
            json=json,
            timeout=self._timeout,
        )

    def put(self, path, json):
        return self._session.put(
            url=self.api_url + path,
            json=json,
            timeout=self._timeout,
        )

    def patch(self, path, json):
        return self._session.patch(
            url=self.api_url + path,
            json=json,
            timeout=self._timeout,
        )


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
        self._rag = _TimedRAGFlow(self._api_key, self._base_url, self._timeout)

    # --- SDK object → dict converters ---

    @staticmethod
    def _dataset_to_dict(ds: Any) -> dict[str, Any]:
        return {
            "id": str(ds.id or ""),
            "name": str(getattr(ds, "name", "") or ""),
            "tenant_id": str(getattr(ds, "tenant_id", "") or "") or None,
            "permission": str(getattr(ds, "permission", "") or "") or None,
        }

    @staticmethod
    def _chat_to_dict(chat: Any) -> dict[str, Any]:
        dataset_ids = list(getattr(chat, "dataset_ids", None) or [])
        return {
            "id": str(chat.id or ""),
            "name": str(getattr(chat, "name", "") or ""),
            "dataset_ids": dataset_ids,
            # kb_sync reconcile reads chat.get("datasets") or chat.get("knowledgebases")
            "datasets": dataset_ids,
            # Required by resource_is_owned() so the orphan sweep can delete stale chats.
            "tenant_id": str(getattr(chat, "tenant_id", "") or "") or None,
            "permission": str(getattr(chat, "permission", "") or "") or None,
        }

    @staticmethod
    def _doc_to_dict(doc: Any) -> dict[str, Any]:
        return {
            "id": str(doc.id or ""),
            "name": str(getattr(doc, "name", "") or ""),
            "run": str(getattr(doc, "run", "0") or "0"),
        }

    # --- Error classifiers (same patterns preserved from the old httpx client) ---

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

    # --- Dataset operations ---

    async def list_datasets(
        self,
        *,
        name: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        def _sync() -> list[dict[str, Any]]:
            try:
                datasets = self._rag.list_datasets(name=name, id=dataset_id, page_size=50)
                return [self._dataset_to_dict(d) for d in datasets]
            except Exception as exc:
                if self._missing_resource_error(exc, name_filter=bool(name or dataset_id)):
                    return []
                raise RuntimeError(f"Ragflow list_datasets failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def create_dataset(
        self,
        *,
        name: str,
        description: str = "",
        embedding_model: Optional[str] = None,
        chunk_method: str = "naive",
    ) -> dict[str, Any]:
        def _sync() -> dict[str, Any]:
            try:
                ds = self._rag.create_dataset(
                    name=name,
                    description=description,
                    embedding_model=embedding_model,
                    chunk_method=chunk_method,
                )
                return self._dataset_to_dict(ds)
            except Exception as exc:
                raise RuntimeError(f"Ragflow create_dataset failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def delete_datasets(self, dataset_ids: list[str]) -> None:
        if not dataset_ids:
            return

        def _sync() -> None:
            try:
                self._rag.delete_datasets(ids=dataset_ids)
            except Exception as exc:
                if self._already_gone_error(exc):
                    return
                raise RuntimeError(f"Ragflow delete_datasets failed: {exc}") from exc

        await asyncio.to_thread(_sync)

    # --- Document operations ---
    # Build a minimal DataSet shell from the ID to avoid an extra list API call.
    # DataSet only uses self.id for URL construction so this is safe.

    def _dataset_shell(self, dataset_id: str) -> DataSet:
        return DataSet(self._rag, {"id": dataset_id})

    async def list_documents(
        self,
        dataset_id: str,
        *,
        name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        def _sync() -> list[dict[str, Any]]:
            try:
                ds = self._dataset_shell(dataset_id)
                docs = ds.list_documents(name=name, page_size=100)
                return [self._doc_to_dict(d) for d in docs]
            except Exception as exc:
                if self._missing_resource_error(exc, name_filter=bool(name)):
                    return []
                raise RuntimeError(f"Ragflow list_documents failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def upload_document(
        self,
        dataset_id: str,
        file_name: str,
        content: bytes,
    ) -> list[dict[str, Any]]:
        def _sync() -> list[dict[str, Any]]:
            try:
                ds = self._dataset_shell(dataset_id)
                docs = ds.upload_documents([{"display_name": file_name, "blob": content}])
                return [self._doc_to_dict(d) for d in docs]
            except Exception as exc:
                raise RuntimeError(f"Ragflow upload_document failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def delete_documents(
        self,
        dataset_id: str,
        document_ids: list[str],
    ) -> None:
        if not document_ids:
            return

        def _sync() -> None:
            try:
                ds = self._dataset_shell(dataset_id)
                ds.delete_documents(ids=document_ids)
            except Exception as exc:
                raise RuntimeError(f"Ragflow delete_documents failed: {exc}") from exc

        await asyncio.to_thread(_sync)

    async def parse_documents(
        self,
        dataset_id: str,
        document_ids: list[str],
    ) -> None:
        if not document_ids:
            return

        def _sync() -> None:
            try:
                ds = self._dataset_shell(dataset_id)
                ds.async_parse_documents(document_ids)
            except Exception as exc:
                raise RuntimeError(f"Ragflow parse_documents failed: {exc}") from exc

        await asyncio.to_thread(_sync)

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

    async def list_chunks_for_document(
        self,
        dataset_id: str,
        document_id: str,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Pull all parsed chunks for a Ragflow document, paginating as needed."""
        def _sync() -> list[dict[str, Any]]:
            try:
                doc = Document(self._rag, {"id": document_id, "dataset_id": dataset_id})
                all_chunks: list[dict[str, Any]] = []
                page = 1
                while True:
                    chunks = doc.list_chunks(page=page, page_size=page_size)
                    if not chunks:
                        break
                    for c in chunks:
                        content = getattr(c, "content", "") or ""
                        if content.strip():
                            all_chunks.append({"content": content, "chunk_id": getattr(c, "id", "")})
                    if len(chunks) < page_size:
                        break
                    page += 1
                return all_chunks
            except Exception as exc:
                raise RuntimeError(f"Ragflow list_chunks_for_document failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    # --- Chat operations ---

    async def list_chats(
        self,
        *,
        name: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        def _sync() -> list[dict[str, Any]]:
            try:
                chats = self._rag.list_chats(name=name, id=chat_id, page_size=50)
                return [self._chat_to_dict(c) for c in chats]
            except Exception as exc:
                if self._missing_resource_error(exc, name_filter=bool(name or chat_id)):
                    return []
                raise RuntimeError(f"Ragflow list_chats failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def create_chat(
        self,
        *,
        name: str,
        dataset_ids: list[str],
        llm_id: Optional[str] = None,
        description: str = "Cria bot synced from Moodle",
    ) -> dict[str, Any]:
        def _try_create(include_llm_id: bool) -> dict[str, Any]:
            kwargs: dict[str, Any] = {
                "name": name,
                "dataset_ids": dataset_ids,
                "description": description,
            }
            if include_llm_id and llm_id:
                kwargs["llm_id"] = llm_id
            chat = self._rag.create_chat(**kwargs)
            return self._chat_to_dict(chat)

        def _sync() -> dict[str, Any]:
            try:
                return _try_create(True)
            except Exception as exc:
                # Ragflow >=0.26 strictly validates llm_id and rejects identifiers that are
                # not the full "<model>@<key>@<provider>" form. Retry without llm_id so
                # Ragflow applies the tenant default.
                message = str(exc).lower()
                if llm_id and (
                    "llm_id" in message
                    or "doesn't exist" in message
                    or "does not exist" in message
                ):
                    logger.warning(
                        "Ragflow rejected llm_id '%s' (%s); retrying chat '%s' create with tenant default model",
                        llm_id,
                        exc,
                        name,
                    )
                    try:
                        return _try_create(False)
                    except Exception as exc2:
                        raise RuntimeError(f"Ragflow create_chat failed: {exc2}") from exc2
                raise RuntimeError(f"Ragflow create_chat failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def patch_chat(
        self,
        chat_id: str,
        *,
        dataset_ids: list[str],
    ) -> dict[str, Any]:
        # Build a minimal Chat shell — update() only uses self.id for the URL.
        def _sync() -> dict[str, Any]:
            try:
                chat = Chat(self._rag, {"id": chat_id})
                chat.update({"dataset_ids": dataset_ids})
                return {"id": chat_id, "dataset_ids": dataset_ids, "datasets": dataset_ids}
            except Exception as exc:
                raise RuntimeError(f"Ragflow patch_chat failed: {exc}") from exc

        return await asyncio.to_thread(_sync)

    async def delete_chats(self, chat_ids: list[str]) -> None:
        if not chat_ids:
            return

        def _sync() -> None:
            try:
                self._rag.delete_chats(ids=chat_ids)
            except Exception as exc:
                if self._already_gone_error(exc):
                    return
                raise RuntimeError(f"Ragflow delete_chats failed: {exc}") from exc

        await asyncio.to_thread(_sync)
