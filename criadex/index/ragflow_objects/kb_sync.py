"""
Sync Criadex groups and documents to Ragflow datasets and chat assistants.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Optional

from aiomysql import Pool

from criadex.database.api import GroupDatabaseAPI
from criadex.database.tables.models.generic import GenericModelsModel
from criadex.index.ragflow_objects.kb_client import RagflowKbClient, kb_sync_enabled
from criadex.schemas import GroupConfig, IndexType

logger = logging.getLogger(__name__)

DOCUMENT_INDEX_SUFFIX = "-document-index"
QUESTION_INDEX_SUFFIX = "-question-index"

# Extensions Ragflow would parse as binary; node payloads are always UTF-8 text.
_BINARY_UPLOAD_EXTENSIONS = {
    ".docx", ".doc", ".pdf", ".html", ".htm", ".png", ".jpg", ".jpeg",
    ".gif", ".bmp", ".xlsx", ".xls", ".pptx", ".ppt", ".rtf", ".odt",
}


def ragflow_upload_filename(file_name: str) -> str:
    """Map a Criadex document name to the filename used for Ragflow upload."""
    base, ext = os.path.splitext(file_name)
    if ext.lower() in _BINARY_UPLOAD_EXTENSIONS:
        return f"{base}.txt"
    return file_name


def ragflow_document_lookup_names(document_name: str) -> list[str]:
    """Candidate Ragflow document names (upload name first, then legacy original)."""
    upload_name = ragflow_upload_filename(document_name)
    if upload_name == document_name:
        return [document_name]
    return [upload_name, document_name]


def sanitize_ragflow_name(value: str, *, max_len: int = 128) -> str:
    """Keep Ragflow-safe BMP names within length limits."""
    text = "".join(ch for ch in (value or "").strip() if ord(ch) <= 0xFFFF)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = "cria-group"
    return text[:max_len]


def bot_name_from_group(group_name: str) -> Optional[str]:
    if group_name.endswith(DOCUMENT_INDEX_SUFFIX):
        return group_name[: -len(DOCUMENT_INDEX_SUFFIX)]
    if group_name.endswith(QUESTION_INDEX_SUFFIX):
        return group_name[: -len(QUESTION_INDEX_SUFFIX)]
    return None


def should_sync_group_to_ragflow(group_name: str) -> bool:
    """Only mirror document indexes in Ragflow; question/FAQ indexes stay Criadex-only."""
    return group_name.endswith(DOCUMENT_INDEX_SUFFIX)


def resolve_requires_documents(config: GroupConfig) -> bool:
    """Whether to create a Ragflow dataset for this document-index group.

    When Criabot does not pass ``requires_documents`` (older images), infer from Cria's
    bot naming: no-upload bots use a bare numeric Criabot name (e.g. ``167``), while
    upload-required bots use ``<bot_id>-<intent_id>`` (e.g. ``166-160``).
    """
    if config.requires_documents is not None:
        return bool(config.requires_documents)

    bot_name = bot_name_from_group(config.name)
    if bot_name and bot_name.isdigit():
        return False
    return True


def resource_is_owned(resource: dict[str, Any]) -> bool:
    try:
        if resource.get("permission") == "me":
            return True
        tenant = str(os.getenv("RAGFLOW_TENANT_ID", "")).strip()
        return bool(tenant) and str(resource.get("tenant_id") or "") == tenant
    except Exception:
        return False


def dataset_access_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "don't own" in message
        or "do not own" in message
        or "lacks permission" in message
        or "doesn't exist" in message
        or "does not exist" in message
    )


def chunk_method_for_group(group_type: int) -> str:
    if group_type == IndexType.QUESTION.value:
        return "qa"
    return "naive"


def build_document_bytes(file_name: str, file_contents: dict) -> bytes:
    parts: list[str] = []
    if "nodes" in file_contents:
        for node_data in file_contents.get("nodes") or []:
            if isinstance(node_data, dict):
                text = str(node_data.get("text", "")).strip()
            else:
                text = str(getattr(node_data, "text", "")).strip()
            if text:
                parts.append(text)
    elif "questions" in file_contents:
        for question in file_contents.get("questions") or []:
            text = str(question).strip()
            if text:
                parts.append(f"Q: {text}")
        if "answer" in file_contents:
            answer = str(file_contents.get("answer", "")).strip()
            if answer:
                parts.append(f"A: {answer}")

    body = "\n\n".join(parts).strip()
    if not body:
        body = f"(empty content for {file_name})"

    if "." not in file_name:
        return body.encode("utf-8")

    return body.encode("utf-8")


class RagflowKbSync:
    def __init__(
        self,
        mysql_pool: Pool,
        mysql_api: GroupDatabaseAPI,
        client: Optional[RagflowKbClient] = None,
    ) -> None:
        self._pool = mysql_pool
        self._mysql_api = mysql_api
        self._client = client or RagflowKbClient()

    async def _group_exists(self, group_name: str) -> bool:
        """Return False when a background sync task races group deletion."""
        try:
            group = await self._mysql_api.groups.retrieve(name=group_name)
            return group is not None
        except Exception:
            return False

    async def _read_link(self, group_name: str) -> Optional[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT group_name, ragflow_dataset_id, ragflow_dataset_name, ragflow_chat_id, updated_at
                    FROM GroupRagflowLinks
                    WHERE group_name = %s
                    LIMIT 1
                    """,
                    (group_name,),
                )
                row = await cursor.fetchone()
        if not row:
            return None
        return {
            "group_name": row[0],
            "ragflow_dataset_id": row[1],
            "ragflow_dataset_name": row[2],
            "ragflow_chat_id": row[3],
            "updated_at": row[4],
        }

    async def _write_link(
        self,
        *,
        group_name: str,
        dataset_id: str,
        dataset_name: str,
        chat_id: Optional[str] = None,
    ) -> None:
        now = int(time.time() * 1000)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO GroupRagflowLinks
                        (group_name, ragflow_dataset_id, ragflow_dataset_name, ragflow_chat_id, updated_at)
                    VALUES (%s, %s, %s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                        ragflow_dataset_id = new.ragflow_dataset_id,
                        ragflow_dataset_name = new.ragflow_dataset_name,
                        ragflow_chat_id = COALESCE(new.ragflow_chat_id, GroupRagflowLinks.ragflow_chat_id),
                        updated_at = new.updated_at
                    """,
                    (group_name, dataset_id, dataset_name, chat_id, now),
                )

    async def _delete_link(self, group_name: str) -> None:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM GroupRagflowLinks WHERE group_name = %s",
                    (group_name,),
                )

    async def _clear_stale_chat_link(self, group_name: str) -> None:
        """Null-out the ragflow_chat_id for a group when the chat no longer exists in Ragflow."""
        now = int(time.time() * 1000)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE GroupRagflowLinks SET ragflow_chat_id = NULL, updated_at = %s WHERE group_name = %s",
                    (now, group_name),
                )

    async def _list_all_links(self) -> list[dict[str, Any]]:
        """Return all rows from GroupRagflowLinks."""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT group_name, ragflow_dataset_id, ragflow_dataset_name, ragflow_chat_id, updated_at
                    FROM GroupRagflowLinks
                    """
                )
                rows = await cursor.fetchall()
        return [
            {
                "group_name": row[0],
                "ragflow_dataset_id": row[1],
                "ragflow_dataset_name": row[2],
                "ragflow_chat_id": row[3],
                "updated_at": row[4],
            }
            for row in (rows or [])
        ]

    async def _resolve_ragflow_model_name(self, model_id: int, *, model_kind: str) -> Optional[str]:
        if model_id <= 0:
            return None

        generic: Optional[GenericModelsModel] = await self._mysql_api.generic_models.retrieve(model_id=model_id)
        if generic and (generic.provider_type or "").lower() == "ragflow":
            config = generic.config or {}
            api_model = str(config.get("api_model") or config.get("llm_name") or "").strip()
            llm_factory = str(config.get("llm_factory") or "").strip()
            if api_model:
                # Ragflow requires "<model_name>@<provider>" format
                if llm_factory and "@" not in api_model:
                    return f"{api_model}@{llm_factory}"
                return api_model

        return None

    async def _dataset_is_accessible(self, dataset_id: str) -> bool:
        if not dataset_id:
            return False
        try:
            datasets = await self._client.list_datasets(dataset_id=dataset_id)
        except Exception:
            return False
        if not datasets:
            return False
        return resource_is_owned(datasets[0])

    async def _delete_owned_datasets_by_name(self, dataset_name: str, *, skip_ids: Optional[set[str]] = None) -> list[str]:
        """Delete all owned Ragflow datasets matching ``dataset_name`` (orphan cleanup)."""
        skip = skip_ids or set()
        deleted: list[str] = []
        datasets = await self._client.list_datasets(name=dataset_name)
        for dataset in datasets:
            dataset_id = str(dataset.get("id") or "")
            if not dataset_id or dataset_id in skip or not resource_is_owned(dataset):
                continue
            try:
                await self._client.delete_datasets([dataset_id])
                deleted.append(dataset_id)
            except RuntimeError as exc:
                if not self._client._already_gone_error(exc):
                    logger.warning(
                        "Ragflow orphan dataset deletion failed for '%s' (%s): %s",
                        dataset_name,
                        dataset_id,
                        exc,
                    )
        return deleted

    async def _delete_owned_chats_by_name(self, chat_name: str, *, skip_ids: Optional[set[str]] = None) -> list[str]:
        """Delete owned Ragflow chats matching ``chat_name`` (orphan cleanup)."""
        skip = skip_ids or set()
        deleted: list[str] = []
        chats = await self._client.list_chats(name=chat_name)
        for chat in chats:
            chat_id = str(chat.get("id") or "")
            if not chat_id or chat_id in skip or not resource_is_owned(chat):
                continue
            try:
                await self._client.delete_chats([chat_id])
                deleted.append(chat_id)
            except RuntimeError as exc:
                if not self._client._already_gone_error(exc):
                    logger.warning(
                        "Ragflow orphan chat deletion failed for '%s' (%s): %s",
                        chat_name,
                        chat_id,
                        exc,
                    )
        return deleted

    def _schedule_chat_dataset_link_retry(
        self,
        *,
        chat_id: str,
        dataset_id: str,
        group_name: str,
    ) -> None:
        import asyncio as _asyncio

        _asyncio.create_task(
            self._retry_chat_link_after_parse(
                chat_id=chat_id,
                dataset_id=dataset_id,
                group_name=group_name,
            )
        )
        logger.info(
            "Ragflow chat '%s' dataset link deferred: documents still parsing",
            chat_id,
        )

    async def _patch_chat_dataset_link(
        self,
        *,
        chat_id: str,
        dataset_id: str,
        group_name: str,
    ) -> None:
        if not dataset_id:
            return
        try:
            await self._client.patch_chat(chat_id, dataset_ids=[dataset_id])
        except Exception as exc:
            exc_str = str(exc).lower()
            if "parsed file" in exc_str:
                self._schedule_chat_dataset_link_retry(
                    chat_id=chat_id,
                    dataset_id=dataset_id,
                    group_name=group_name,
                )
            else:
                logger.warning(
                    "Ragflow chat '%s' dataset link update failed: %s", chat_id, exc
                )

    async def _ensure_dataset_for_group(self, config: GroupConfig) -> dict[str, Any]:
        if not await self._group_exists(config.name):
            return {}
        dataset_name = sanitize_ragflow_name(config.name)
        existing_link = await self._read_link(config.name)
        if existing_link:
            dataset_id = str(existing_link.get("ragflow_dataset_id") or "")
            if not dataset_id:
                return existing_link
            if await self._dataset_is_accessible(dataset_id):
                return existing_link
            logger.info(
                "Clearing stale Ragflow dataset link for group '%s' (dataset %s)",
                config.name,
                dataset_id,
            )
            await self._delete_link(config.name)

        datasets = await self._client.list_datasets(name=dataset_name)
        if datasets:
            # Prefer a dataset owned/usable by this server/API key (permission == 'me' or tenant match).
            selected = None
            for ds in datasets:
                if resource_is_owned(ds):
                    selected = ds
                    break
            # If none owned by us, do not reuse potentially-unowned dataset — create a new one.
            if selected is None:
                selected = None
            else:
                dataset = selected
                dataset_id = str(dataset.get("id") or "")
                if dataset_id:
                    await self._write_link(
                        group_name=config.name,
                        dataset_id=dataset_id,
                        dataset_name=dataset_name,
                    )
                    return await self._read_link(config.name) or {
                        "group_name": config.name,
                        "ragflow_dataset_id": dataset_id,
                        "ragflow_dataset_name": dataset_name,
                        "ragflow_chat_id": None,
                    }

        if not await self._group_exists(config.name):
            return {}

        embedding_model = await self._resolve_ragflow_model_name(
            config.embedding_model_id,
            model_kind="embedding",
        )
        try:
            created = await self._client.create_dataset(
                name=dataset_name,
                description=f"Cria index group: {config.name}",
                embedding_model=embedding_model,
                chunk_method=chunk_method_for_group(IndexType[config.type].value),
            )
        except RuntimeError as exc:
            message = str(exc)
            # Some Ragflow deployments reject legacy embedding identifiers
            # (e.g. "embed-english-v2.0") and require vendor-qualified IDs.
            # Fall back to server default embedding model to avoid blocking sync.
            if (
                embedding_model
                and "embedding model identifier" in message.lower()
                and "must follow" in message.lower()
            ):
                logger.warning(
                    "Ragflow rejected embedding_model '%s' for group '%s'; retrying with default embedding",
                    embedding_model,
                    config.name,
                )
                created = await self._client.create_dataset(
                    name=dataset_name,
                    description=f"Cria index group: {config.name}",
                    embedding_model=None,
                    chunk_method=chunk_method_for_group(IndexType[config.type].value),
                )
            else:
                raise
        dataset_id = str(created.get("id") or "")
        if not dataset_id:
            raise RuntimeError(f"Ragflow dataset created without id for group '{config.name}'")

        await self._write_link(
            group_name=config.name,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
        )
        logger.info(
            "Created Ragflow dataset '%s' (%s) for Criadex group '%s'",
            dataset_name,
            dataset_id,
            config.name,
        )
        return await self._read_link(config.name) or {
            "group_name": config.name,
            "ragflow_dataset_id": dataset_id,
            "ragflow_dataset_name": dataset_name,
            "ragflow_chat_id": None,
        }

    async def _retry_chat_link_after_parse(
        self,
        *,
        chat_id: str,
        dataset_id: str,
        group_name: str,
        retry_interval: float = 10.0,
        max_attempts: int = 30,  # 30 × 10s = 5 min max
    ) -> None:
        """Background retry: keep trying to link chat to dataset until parsing completes."""
        import asyncio as _asyncio
        for attempt in range(max_attempts):
            await _asyncio.sleep(retry_interval)
            try:
                await self._client.patch_chat(chat_id, dataset_ids=[dataset_id])
                logger.info(
                    "Ragflow chat '%s' successfully linked to dataset '%s' after parse (attempt %d)",
                    chat_id,
                    dataset_id,
                    attempt + 1,
                )
                return
            except Exception as exc:
                if "parsed file" in str(exc).lower():
                    # Still parsing — keep retrying
                    continue
                logger.warning(
                    "Ragflow chat '%s' deferred link failed (attempt %d): %s",
                    chat_id,
                    attempt + 1,
                    exc,
                )
                return
        logger.warning(
            "Ragflow chat '%s' dataset link gave up after %d attempts; "
            "run /ragflow/reconcile to repair",
            chat_id,
            max_attempts,
        )

    async def _ensure_chat_for_bot(
        self,
        *,
        bot_name: str,
        dataset_id: str,
        llm_model_id: int,
        group_name: str,
    ) -> Optional[str]:
        if not await self._group_exists(group_name):
            return None
        chat_name = sanitize_ragflow_name(bot_name, max_len=120)
        existing = await self._read_link(group_name)
        if existing and existing.get("ragflow_chat_id"):
            # Chat already linked — patch its dataset list if needed (e.g. after first upload).
            chat_id = str(existing["ragflow_chat_id"])
            await self._patch_chat_dataset_link(
                chat_id=chat_id,
                dataset_id=dataset_id,
                group_name=group_name,
            )
            return chat_id

        chats = await self._client.list_chats(name=chat_name)
        if chats:
            # Prefer a chat owned/usable by this server/API key (permission == 'me' or tenant match).
            selected = None
            for ch in chats:
                if resource_is_owned(ch):
                    selected = ch
                    break
            if selected is not None:
                chat_id = str(selected.get("id") or "")
                if chat_id:
                    await self._patch_chat_dataset_link(
                        chat_id=chat_id,
                        dataset_id=dataset_id,
                        group_name=group_name,
                    )
                    await self._write_link(
                        group_name=group_name,
                        dataset_id=dataset_id,
                        dataset_name=sanitize_ragflow_name(existing.get("ragflow_dataset_name") if existing else group_name),
                        chat_id=chat_id,
                    )
                    return chat_id

        llm_id = await self._resolve_ragflow_model_name(llm_model_id, model_kind="chat")
        # Use an empty dataset list when the dataset has no parsed files yet so Ragflow
        # accepts the creation.  The chat will be patched with the real dataset_id on first
        # successful document upload.
        ids_for_create: list[str] = [dataset_id] if dataset_id else []
        try:
            created = await self._client.create_chat(
                name=chat_name,
                dataset_ids=ids_for_create,
                llm_id=llm_id,
                description=f"Cria bot '{bot_name}' synced from Moodle",
            )
        except RuntimeError as exc:
            exc_str = str(exc).lower()
            if "duplicated chat name" in exc_str:
                for chat in await self._client.list_chats():
                    if str(chat.get("name") or "") != chat_name or not chat.get("id"):
                        continue
                    if not resource_is_owned(chat):
                        continue
                    chat_id = str(chat["id"])
                    await self._patch_chat_dataset_link(
                        chat_id=chat_id,
                        dataset_id=dataset_id,
                        group_name=group_name,
                    )
                    await self._write_link(
                        group_name=group_name,
                        dataset_id=dataset_id,
                        dataset_name=sanitize_ragflow_name(existing.get("ragflow_dataset_name") if existing else group_name),
                        chat_id=chat_id,
                    )
                    return chat_id
            elif "parsed file" in exc_str:
                # Dataset has no parsed documents yet — create chat unlinked (dataset_ids=[]).
                logger.info(
                    "Ragflow dataset '%s' has no parsed files; creating chat '%s' unlinked",
                    dataset_id,
                    chat_name,
                )
                try:
                    created = await self._client.create_chat(
                        name=chat_name,
                        dataset_ids=[],
                        llm_id=llm_id,
                        description=f"Cria bot '{bot_name}' synced from Moodle",
                    )
                except RuntimeError:
                    return None
            else:
                raise
        chat_id = str(created.get("id") or "")
        if not chat_id:
            logger.warning("Ragflow chat created without id for bot '%s'", bot_name)
            return None

        await self._write_link(
            group_name=group_name,
            dataset_id=dataset_id,
            dataset_name=sanitize_ragflow_name(existing.get("ragflow_dataset_name") if existing else group_name),
            chat_id=chat_id,
        )
        logger.info(
            "Created Ragflow chat assistant '%s' (%s) for bot '%s'",
            chat_name,
            chat_id,
            bot_name,
        )
        return chat_id

    async def sync_group_create(self, config: GroupConfig) -> None:
        if not kb_sync_enabled() or not should_sync_group_to_ragflow(config.name):
            return
        if not await self._group_exists(config.name):
            logger.info(
                "Ragflow group create skipped; Criadex group '%s' no longer exists",
                config.name,
            )
            return

        requires_documents = resolve_requires_documents(config)

        try:
            if not requires_documents:
                await self._sync_chat_for_document_group(
                    group_name=config.name,
                    dataset_id="",
                    llm_model_id=config.llm_model_id,
                )
                return

            link = await self._ensure_dataset_for_group(config)
            dataset_id = str(link.get("ragflow_dataset_id") or "")
            # Create chat immediately so the bot appears in Ragflow without requiring a document upload.
            if dataset_id:
                await self._sync_chat_for_document_group(
                    group_name=config.name,
                    dataset_id=dataset_id,
                    llm_model_id=config.llm_model_id,
                )
        except Exception as exc:
            logger.warning(
                "Ragflow KB sync skipped for group '%s' on create: %s",
                config.name,
                exc,
            )

    async def _sync_chat_for_document_group(
        self,
        *,
        group_name: str,
        dataset_id: str,
        llm_model_id: int,
    ) -> None:
        if not group_name.endswith(DOCUMENT_INDEX_SUFFIX):
            return
        bot_name = bot_name_from_group(group_name)
        if not bot_name:
            return
        try:
            await self._ensure_chat_for_bot(
                bot_name=bot_name,
                dataset_id=dataset_id,
                llm_model_id=llm_model_id,
                group_name=group_name,
            )
        except Exception as exc:
            logger.warning(
                "Ragflow chat sync skipped for group '%s': %s",
                group_name,
                exc,
            )

    async def sync_document_upload(
        self,
        *,
        group_name: str,
        file_name: str,
        file_contents: dict,
        group_config: Optional[GroupConfig] = None,
    ) -> None:
        if not kb_sync_enabled() or not should_sync_group_to_ragflow(group_name):
            return

        try:
            if group_config is None:
                group = await self._mysql_api.groups.retrieve(name=group_name)
                if group is None:
                    return
                group_config = GroupConfig(
                    name=group_name,
                    type=IndexType(group.type).name,
                    llm_model_id=group.llm_model_id,
                    embedding_model_id=group.embedding_model_id,
                    rerank_model_id=group.rerank_model_id,
                )

            document_ids: list[str] = []
            dataset_id = ""
            ragflow_name = ragflow_upload_filename(file_name)
            for attempt in range(3):
                if not await self._group_exists(group_name):
                    return
                link = await self._ensure_dataset_for_group(group_config)
                dataset_id = str(link.get("ragflow_dataset_id") or "")
                if not dataset_id:
                    return

                try:
                    existing_docs = await self._client.list_documents(dataset_id, name=ragflow_name)
                    existing_ids = [str(doc.get("id")) for doc in existing_docs if doc.get("id")]
                    if existing_ids:
                        await self._client.delete_documents(dataset_id, existing_ids)

                    payload = build_document_bytes(file_name, file_contents)

                    uploaded = await self._client.upload_document(
                        dataset_id,
                        ragflow_name,
                        payload,
                    )
                    document_ids = [str(doc.get("id")) for doc in uploaded if doc.get("id")]
                    if document_ids:
                        await self._client.parse_documents(dataset_id, document_ids)
                        parsed = await self._client.wait_for_documents_parsed(dataset_id, document_ids)
                        if not parsed:
                            logger.warning(
                                "Ragflow documents not parsed in time for '%s' in group '%s'; "
                                "chat dataset link will be retried in background",
                                file_name,
                                group_name,
                            )
                    break
                except RuntimeError as exc:
                    if attempt < 2 and dataset_access_error(exc):
                        logger.info(
                            "Ragflow dataset link for group '%s' is not accessible; refreshing link and retrying upload (attempt %d)",
                            group_name,
                            attempt + 1,
                        )
                        await self._delete_link(group_name)
                        continue
                    raise

            if group_name.endswith(DOCUMENT_INDEX_SUFFIX) and dataset_id:
                if await self._group_exists(group_name):
                    await self._sync_chat_for_document_group(
                        group_name=group_name,
                        dataset_id=dataset_id,
                        llm_model_id=group_config.llm_model_id,
                    )

            logger.info(
                "Synced document '%s' to Ragflow dataset %s (%s)",
                file_name,
                dataset_id,
                group_name,
            )
        except Exception as exc:
            logger.warning(
                "Ragflow KB sync skipped for document '%s' in group '%s': %s",
                file_name,
                group_name,
                exc,
            )

    async def sync_document_delete(self, *, group_name: str, document_name: str) -> None:
        if not kb_sync_enabled() or not should_sync_group_to_ragflow(group_name):
            return

        try:
            link = await self._read_link(group_name)
            if not link:
                return
            dataset_id = str(link.get("ragflow_dataset_id") or "")
            if not dataset_id:
                return

            doc_ids: list[str] = []
            for lookup_name in ragflow_document_lookup_names(document_name):
                docs = await self._client.list_documents(dataset_id, name=lookup_name)
                doc_ids = [str(doc.get("id")) for doc in docs if doc.get("id")]
                if doc_ids:
                    break
            if not doc_ids:
                docs = await self._client.list_documents(dataset_id)
                lookup_names = set(ragflow_document_lookup_names(document_name))
                doc_ids = [
                    str(doc.get("id"))
                    for doc in docs
                    if doc.get("id") and str(doc.get("name") or "") in lookup_names
                ]
            if doc_ids:
                await self._client.delete_documents(dataset_id, doc_ids)
                logger.info(
                    "Deleted Ragflow document '%s' from dataset %s",
                    document_name,
                    dataset_id,
                )
        except Exception as exc:
            logger.warning(
                "Ragflow KB delete skipped for document '%s' in group '%s': %s",
                document_name,
                group_name,
                exc,
            )

    async def sync_group_delete(self, *, group_name: str) -> None:
        if not kb_sync_enabled() or not should_sync_group_to_ragflow(group_name):
            return

        try:
            link = await self._read_link(group_name)
            bot_name = bot_name_from_group(group_name)
            chat_name = sanitize_ragflow_name(bot_name, max_len=120) if bot_name else ""
            if not link:
                dataset_name = sanitize_ragflow_name(group_name)
                await self._delete_owned_datasets_by_name(dataset_name)
                if chat_name:
                    await self._delete_owned_chats_by_name(chat_name)
                return

            chat_id = str(link.get("ragflow_chat_id") or "")
            dataset_id = str(link.get("ragflow_dataset_id") or "")
            dataset_name = sanitize_ragflow_name(
                str(link.get("ragflow_dataset_name") or "") or group_name
            )

            deleted_chat_ids: set[str] = set()
            # Delete chat first; a 404/already-gone is safe to ignore.
            if chat_id:
                try:
                    await self._client.delete_chats([chat_id])
                    deleted_chat_ids.add(chat_id)
                except RuntimeError as exc:
                    if not self._client._already_gone_error(exc):
                        logger.warning(
                            "Ragflow chat deletion failed for group '%s' (chat %s): %s",
                            group_name, chat_id, exc,
                        )

            deleted_dataset_ids: set[str] = set()
            # Delete dataset; a 404/already-gone is safe to ignore.
            if dataset_id:
                try:
                    await self._client.delete_datasets([dataset_id])
                    deleted_dataset_ids.add(dataset_id)
                except RuntimeError as exc:
                    if not self._client._already_gone_error(exc):
                        logger.warning(
                            "Ragflow dataset deletion failed for group '%s' (ds %s): %s",
                            group_name, dataset_id, exc,
                        )

            await self._delete_owned_datasets_by_name(
                dataset_name,
                skip_ids=deleted_dataset_ids,
            )
            if chat_name:
                await self._delete_owned_chats_by_name(chat_name, skip_ids=deleted_chat_ids)

            # Always remove the local link so we never reference stale IDs.
            await self._delete_link(group_name)
            logger.info("Removed Ragflow resources for Criadex group '%s'", group_name)
        except Exception as exc:
            logger.warning(
                "Ragflow KB delete skipped for group '%s': %s",
                group_name,
                exc,
            )

    async def reconcile_all_groups(self) -> dict[str, int]:
        """Reconcile Ragflow datasets/chats with local GroupRagflowLinks.

        Scans Ragflow datasets and chats, finds matching Criadex groups by sanitized name,
        and upserts GroupRagflowLinks for groups that exist locally but are missing links.
        Also clears stale links whose Ragflow resources have been deleted (bidirectional sync).
        Returns a summary dict with counts.
        """
        result = {"datasets_linked": 0, "chats_linked": 0, "stale_links_cleared": 0, "skipped": 0}
        if not kb_sync_enabled():
            return result

        try:
            datasets = await self._client.list_datasets()
            chats = await self._client.list_chats()

            # Forward pass: Ragflow → DB (upsert missing links)
            for ds in datasets:
                ds_name = str(ds.get("name") or "").strip()
                ds_id = str(ds.get("id") or "")
                if not ds_name or not ds_id:
                    result["skipped"] += 1
                    continue
                # Try to find a matching Criadex group by dataset name
                group = await self._mysql_api.groups.retrieve(name=ds_name)
                if group is None:
                    result["skipped"] += 1
                    continue
                # Write link if missing or stale
                link = await self._read_link(group.name)
                if not link or str(link.get("ragflow_dataset_id") or "") != ds_id:
                    await self._write_link(group_name=group.name, dataset_id=ds_id, dataset_name=ds_name)
                    result["datasets_linked"] += 1

            # Reconcile chats -> map chat to group by chat name if possible
            for chat in chats:
                chat_name = str(chat.get("name") or "").strip()
                chat_id = str(chat.get("id") or "")
                if not chat_name or not chat_id:
                    result["skipped"] += 1
                    continue
                # Chat names are dataset-like; attempt to match to group
                group = await self._mysql_api.groups.retrieve(name=chat_name)
                if group is None:
                    result["skipped"] += 1
                    continue
                link = await self._read_link(group.name)
                if not link or str(link.get("ragflow_chat_id") or "") != chat_id:
                    # If link missing dataset mapping, try to preserve existing dataset_name
                    dataset_id = str(link.get("ragflow_dataset_id") or "") if link else ""
                    dataset_name = str(link.get("ragflow_dataset_name") or "") if link else ""
                    await self._write_link(group_name=group.name, dataset_id=dataset_id or "", dataset_name=dataset_name, chat_id=chat_id)
                    result["chats_linked"] += 1

                # Repair unlinked chats: if chat has no datasets in Ragflow but we know the dataset_id, re-link.
                chat_ds = chat.get("datasets") or chat.get("knowledgebases") or []
                if not chat_ds:
                    # Re-read link in case it was just written above.
                    link_now = await self._read_link(group.name)
                    ds_id_for_chat = str(link_now.get("ragflow_dataset_id") or "") if link_now else ""
                    if ds_id_for_chat:
                        try:
                            await self._client.patch_chat(chat_id, dataset_ids=[ds_id_for_chat])
                            logger.info(
                                "Reconcile: re-linked chat '%s' to dataset '%s' for group '%s'",
                                chat_id, ds_id_for_chat, group.name,
                            )
                        except Exception as exc:
                            logger.warning(
                                "Reconcile: could not re-link chat '%s': %s", chat_id, exc
                            )

            # Reverse pass: DB → Ragflow (clear stale links whose resources are deleted)
            ragflow_dataset_ids = {str(ds.get("id")) for ds in datasets if ds.get("id")}
            ragflow_chat_ids = {str(ch.get("id")) for ch in chats if ch.get("id")}
            existing_links = await self._list_all_links()
            for link_row in existing_links:
                group_name = link_row["group_name"]
                ds_id = str(link_row.get("ragflow_dataset_id") or "")
                chat_id_val = str(link_row.get("ragflow_chat_id") or "")

                if ds_id and ds_id not in ragflow_dataset_ids:
                    # Dataset was deleted in Ragflow; remove the entire link so next sync recreates it.
                    await self._delete_link(group_name)
                    result["stale_links_cleared"] += 1
                    logger.info(
                        "Cleared stale Ragflow link for group '%s' (dataset '%s' gone)",
                        group_name,
                        ds_id,
                    )
                elif chat_id_val and chat_id_val not in ragflow_chat_ids:
                    # Chat was deleted in Ragflow; clear only the chat_id.
                    await self._clear_stale_chat_link(group_name)
                    result["stale_links_cleared"] += 1
                    logger.info(
                        "Cleared stale Ragflow chat link for group '%s' (chat '%s' gone)",
                        group_name,
                        chat_id_val,
                    )

        except Exception as exc:
            logger.warning("Ragflow reconcile failed: %s", exc, exc_info=True)
        return result
