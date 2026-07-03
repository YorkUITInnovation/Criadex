from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from criadex.index.ragflow_objects.kb_sync import (
    RagflowKbSync,
    bot_name_from_group,
    build_document_bytes,
    ragflow_document_lookup_names,
    ragflow_upload_filename,
    resolve_requires_documents,
    sanitize_ragflow_name,
    should_sync_group_to_ragflow,
)
from criadex.schemas import GroupConfig


def _mock_group_record(**kwargs):
    from types import SimpleNamespace

    defaults = {
        "type": 1,
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 0,
        "name": "bot-document-index",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_sanitize_ragflow_name_truncates() -> None:
    long_name = "a" * 200
    assert len(sanitize_ragflow_name(long_name)) == 128


def test_bot_name_from_group() -> None:
    assert bot_name_from_group("my-bot-document-index") == "my-bot"
    assert bot_name_from_group("my-bot-question-index") == "my-bot"
    assert bot_name_from_group("other") is None


def test_should_sync_group_to_ragflow() -> None:
    assert should_sync_group_to_ragflow("bot-document-index") is True
    assert should_sync_group_to_ragflow("bot-question-index") is False


def test_resolve_requires_documents_explicit_false() -> None:
    config = GroupConfig(
        name="166-160-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
        requires_documents=False,
    )
    assert resolve_requires_documents(config) is False


def test_resolve_requires_documents_infers_no_upload_from_bare_bot_id() -> None:
    config = GroupConfig(
        name="167-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )
    assert resolve_requires_documents(config) is False


def test_resolve_requires_documents_infers_upload_required_from_intent_name() -> None:
    config = GroupConfig(
        name="166-160-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )
    assert resolve_requires_documents(config) is True


def test_build_document_bytes_from_nodes() -> None:
    payload = build_document_bytes(
        "plan.md",
        {"nodes": [{"text": "line one"}, {"text": "line two"}]},
    )
    assert payload.decode("utf-8") == "line one\n\nline two"


def test_build_document_bytes_from_questions() -> None:
    payload = build_document_bytes(
        "faq.txt",
        {"questions": ["what is cria"], "answer": "an assistant"},
    )
    text = payload.decode("utf-8")
    assert "Q: what is cria" in text
    assert "A: an assistant" in text


def test_ragflow_upload_filename_rewrites_binary_extensions() -> None:
    assert ragflow_upload_filename("guide.docx") == "guide.txt"
    assert ragflow_upload_filename("guide.pdf") == "guide.txt"
    assert ragflow_upload_filename("plan.md") == "plan.md"
    assert ragflow_document_lookup_names("guide.docx") == ["guide.txt", "guide.docx"]


@pytest.mark.asyncio
async def test_sync_group_create_skips_when_group_deleted(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(AsyncMock(), mysql_api, client=client)
    await sync.sync_group_create(
        GroupConfig(
            name="185-176-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        )
    )

    client.create_dataset.assert_not_awaited()
    client.create_chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_group_create_creates_dataset_and_chat(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[])
    client.create_dataset = AsyncMock(return_value={"id": "dataset-1", "name": "bot-document-index"})
    client.list_chats = AsyncMock(return_value=[])
    client.create_chat = AsyncMock(return_value={"id": "chat-1", "name": "bot"})

    pool = AsyncMock()
    conn = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.execute = AsyncMock()
    conn.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
    conn.cursor.return_value.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    config = GroupConfig(
        name="bot-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )
    await sync.sync_group_create(config)

    client.create_dataset.assert_awaited_once()
    # Chat should now be created on group create (no upload required)
    client.create_chat.assert_awaited_once()
    assert sync._write_link.await_count >= 1


@pytest.mark.asyncio
async def test_sync_group_create_infers_chat_only_for_bare_bot_id(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[])
    client.create_chat = AsyncMock(return_value={"id": "chat-1", "name": "167"})

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    config = GroupConfig(
        name="167-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )
    await sync.sync_group_create(config)

    client.create_dataset.assert_not_called()
    client.create_chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_group_create_skips_dataset_when_documents_not_required(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[])
    client.create_chat = AsyncMock(return_value={"id": "chat-1", "name": "164"})

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    config = GroupConfig(
        name="164-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
        requires_documents=False,
    )
    await sync.sync_group_create(config)

    client.create_dataset.assert_not_called()
    client.create_chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_group_create_retries_without_embedding_model_on_invalid_identifier(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[])
    client.create_dataset = AsyncMock(
        side_effect=[
            RuntimeError(
                "Ragflow API error 101: Field: <embedding_model> - "
                "Message: <Embedding model identifier must follow <model_name>@<provider> format>"
            ),
            {"id": "dataset-1", "name": "bot-document-index"},
        ]
    )
    client.list_chats = AsyncMock(return_value=[])
    client.create_chat = AsyncMock(return_value={"id": "chat-1", "name": "bot-document-index"})

    pool = AsyncMock()
    mysql_api = AsyncMock()

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()
    sync._resolve_ragflow_model_name = AsyncMock(
        return_value="embed-english-v2.0@cohere@Cohere"
    )

    config = GroupConfig(
        name="bot-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )
    await sync.sync_group_create(config)

    assert client.create_dataset.await_count == 2
    first_call = client.create_dataset.await_args_list[0].kwargs
    second_call = client.create_dataset.await_args_list[1].kwargs
    assert first_call.get("embedding_model") == "embed-english-v2.0@cohere@Cohere"
    assert second_call.get("embedding_model") is None


@pytest.mark.asyncio
async def test_sync_document_upload_replaces_existing_doc(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[{"id": "doc-old", "name": "plan.md"}])
    client.delete_documents = AsyncMock()
    client.upload_document = AsyncMock(return_value=[{"id": "doc-new", "name": "plan.md"}])
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=True)

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._ensure_dataset_for_group = AsyncMock(
        return_value={"ragflow_dataset_id": "dataset-1", "ragflow_dataset_name": "bot-document-index"}
    )
    sync._sync_chat_for_document_group = AsyncMock()

    await sync.sync_document_upload(
        group_name="bot-document-index",
        file_name="plan.md",
        file_contents={"nodes": [{"text": "hello"}]},
        group_config=GroupConfig(
            name="bot-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        ),
    )

    client.delete_documents.assert_awaited_once_with("dataset-1", ["doc-old"])
    client.upload_document.assert_awaited_once()
    upload_args = client.upload_document.await_args
    assert upload_args.args[1] == "plan.md"
    client.parse_documents.assert_awaited_once_with("dataset-1", ["doc-new"])
    client.wait_for_documents_parsed.assert_awaited_once_with("dataset-1", ["doc-new"])
    sync._sync_chat_for_document_group.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_document_upload_rewrites_docx_name_for_ragflow(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[])
    client.upload_document = AsyncMock(return_value=[{"id": "doc-new", "name": "guide.txt"}])
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=True)

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._ensure_dataset_for_group = AsyncMock(
        return_value={"ragflow_dataset_id": "dataset-1", "ragflow_dataset_name": "bot-document-index"}
    )
    sync._sync_chat_for_document_group = AsyncMock()

    await sync.sync_document_upload(
        group_name="bot-document-index",
        file_name="guide.docx",
        file_contents={"nodes": [{"text": "hello docx"}]},
        group_config=GroupConfig(
            name="bot-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        ),
    )

    upload_args = client.upload_document.await_args
    assert upload_args.args[1] == "guide.txt"
    assert upload_args.args[2].decode("utf-8") == "hello docx"


@pytest.mark.asyncio
async def test_sync_document_upload_retries_when_dataset_not_owned(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[])
    client.upload_document = AsyncMock(
        side_effect=[
            RuntimeError("Ragflow API error 102: You don't own the dataset old-ds"),
            [{"id": "doc-new", "name": "plan.md"}],
        ]
    )
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=True)

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._ensure_dataset_for_group = AsyncMock(
        side_effect=[
            {"ragflow_dataset_id": "old-ds", "ragflow_dataset_name": "bot-document-index"},
            {"ragflow_dataset_id": "new-ds", "ragflow_dataset_name": "bot-document-index"},
        ]
    )
    sync._delete_link = AsyncMock()
    sync._sync_chat_for_document_group = AsyncMock()

    await sync.sync_document_upload(
        group_name="bot-document-index",
        file_name="plan.md",
        file_contents={"nodes": [{"text": "hello"}]},
        group_config=GroupConfig(
            name="bot-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        ),
    )

    sync._delete_link.assert_awaited_once_with("bot-document-index")
    assert sync._ensure_dataset_for_group.await_count == 2
    upload_calls = client.upload_document.await_args_list
    assert upload_calls[0].args[0] == "old-ds"
    assert upload_calls[1].args[0] == "new-ds"
    client.parse_documents.assert_awaited_once_with("new-ds", ["doc-new"])
    sync._sync_chat_for_document_group.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_dataset_clears_stale_link_before_reuse(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_TENANT_ID", "tenant-1")

    client = AsyncMock()
    client.list_datasets = AsyncMock(
        side_effect=[
            [],
            [{"id": "ds-owned", "name": "169-161-document-index", "permission": "me"}],
        ]
    )

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._read_link = AsyncMock(
        side_effect=[
            {
                "group_name": "169-161-document-index",
                "ragflow_dataset_id": "stale-ds",
                "ragflow_dataset_name": "169-161-document-index",
                "ragflow_chat_id": "chat-old",
            },
            {
                "group_name": "169-161-document-index",
                "ragflow_dataset_id": "ds-owned",
                "ragflow_dataset_name": "169-161-document-index",
                "ragflow_chat_id": None,
            },
        ]
    )
    sync._delete_link = AsyncMock()
    sync._write_link = AsyncMock()

    config = GroupConfig(
        name="169-161-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )
    link = await sync._ensure_dataset_for_group(config)

    sync._delete_link.assert_awaited_once_with("169-161-document-index")
    assert link["ragflow_dataset_id"] == "ds-owned"
    client.create_dataset.assert_not_called()


@pytest.mark.asyncio
async def test_sync_group_delete_cleans_orphan_datasets_by_name(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.delete_chats = AsyncMock()
    client.delete_datasets = AsyncMock()
    client.list_chats = AsyncMock(return_value=[])
    client.list_datasets = AsyncMock(
        return_value=[
            {"id": "orphan-ds", "name": "169-161-document-index", "permission": "me"},
        ]
    )

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._read_link = AsyncMock(
        return_value={
            "group_name": "169-161-document-index",
            "ragflow_dataset_id": "linked-ds",
            "ragflow_dataset_name": "169-161-document-index",
            "ragflow_chat_id": "chat-1",
        }
    )
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="169-161-document-index")

    deleted_ids = [call.args[0][0] for call in client.delete_datasets.await_args_list]
    assert "linked-ds" in deleted_ids
    assert "orphan-ds" in deleted_ids
    client.delete_chats.assert_awaited()
    sync._delete_link.assert_awaited_once()


def _mock_chat_obj(id="chat-1", name="bot", dataset_ids=None):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.id = id
    m.name = name
    m.dataset_ids = dataset_ids or []
    return m


def _mock_dataset_obj(id="ds-1", name="ds", tenant_id=None, permission="me"):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.id = id
    m.name = name
    m.tenant_id = tenant_id
    m.permission = permission
    return m


@pytest.mark.asyncio
async def test_list_datasets_permission_error_treated_as_missing(monkeypatch) -> None:
    from unittest.mock import MagicMock
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()
    client._rag.list_datasets.side_effect = Exception(
        "108: User 'tenant' lacks permission for dataset 'missing'"
    )

    datasets = await client.list_datasets(name="missing")
    assert datasets == []


@pytest.mark.asyncio
async def test_list_chats_missing_error_treated_as_empty(monkeypatch) -> None:
    from unittest.mock import MagicMock
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()
    client._rag.list_chats.side_effect = Exception("102: The chat doesn't exist")

    chats = await client.list_chats(name="missing-chat")
    assert chats == []


@pytest.mark.asyncio
async def test_list_chats_sdk_objects_converted_to_dicts(monkeypatch) -> None:
    """list_chats converts SDK Chat objects to the dict format kb_sync expects."""
    from unittest.mock import MagicMock
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()
    client._rag.list_chats.return_value = [_mock_chat_obj(id="chat-1", name="bot", dataset_ids=["ds-1"])]

    chats = await client.list_chats()
    assert len(chats) == 1
    assert chats[0]["id"] == "chat-1"
    assert chats[0]["name"] == "bot"
    # Both dataset_ids and datasets alias must be present for kb_sync reconcile
    assert chats[0]["dataset_ids"] == ["ds-1"]
    assert chats[0]["datasets"] == ["ds-1"]


@pytest.mark.asyncio
async def test_create_chat_retries_without_llm_id_when_rejected(monkeypatch) -> None:
    """Ragflow >=0.26 rejects non-fully-qualified llm_id; create_chat must retry
    without it (tenant default) instead of failing the whole bot sync."""
    from unittest.mock import MagicMock, call
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()
    client._rag.create_chat.side_effect = [
        Exception("`llm_id` gpt-3.5-turbo@OpenAI doesn't exist"),
        _mock_chat_obj(id="chat-default", name="bot"),
    ]

    data = await client.create_chat(
        name="bot",
        dataset_ids=[],
        llm_id="gpt-3.5-turbo@OpenAI",
    )

    assert data["id"] == "chat-default"
    assert data["name"] == "bot"
    assert client._rag.create_chat.call_count == 2
    # First attempt includes llm_id; retry must drop it so Ragflow uses the tenant default.
    first_kwargs = client._rag.create_chat.call_args_list[0].kwargs
    second_kwargs = client._rag.create_chat.call_args_list[1].kwargs
    assert first_kwargs.get("llm_id") == "gpt-3.5-turbo@OpenAI"
    assert "llm_id" not in second_kwargs


@pytest.mark.asyncio
async def test_create_chat_does_not_retry_on_unrelated_error(monkeypatch) -> None:
    from unittest.mock import MagicMock
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()
    client._rag.create_chat.side_effect = Exception("internal boom")

    with pytest.raises(RuntimeError, match="internal boom"):
        await client.create_chat(name="bot", dataset_ids=[], llm_id="gpt-3.5-turbo@OpenAI")
    assert client._rag.create_chat.call_count == 1


@pytest.mark.asyncio
async def test_resolve_ragflow_model_name_uses_qualified_config(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    pool = AsyncMock()
    mysql_api = AsyncMock()
    model = AsyncMock()
    model.provider_type = "ragflow"
    model.config = {
        "api_model": "embed-english-v2.0@cohere@Cohere",
        "llm_factory": "Cohere",
    }
    mysql_api.generic_models.retrieve = AsyncMock(return_value=model)

    sync = RagflowKbSync(pool, mysql_api)
    result = await sync._resolve_ragflow_model_name(42, model_kind="embedding")

    assert result == "embed-english-v2.0@cohere@Cohere"


@pytest.mark.asyncio
async def test_resolve_ragflow_model_name_returns_none_for_unqualified_config(monkeypatch) -> None:
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    pool = AsyncMock()
    mysql_api = AsyncMock()
    model = AsyncMock()
    model.provider_type = "ragflow"
    model.config = {
        "api_model": "embed-english-v2.0",
        "llm_factory": "Cohere",
    }
    mysql_api.generic_models.retrieve = AsyncMock(return_value=model)

    sync = RagflowKbSync(pool, mysql_api)
    with patch(
        "criadex.index.ragflow_objects.kb_sync.resolve_qualified_model_id",
        new=AsyncMock(return_value=None),
    ):
        result = await sync._resolve_ragflow_model_name(42, model_kind="embedding")

    assert result is None


@pytest.mark.asyncio
async def test_ensure_chat_defers_on_empty_dataset(monkeypatch) -> None:
    """When Ragflow rejects chat creation because the dataset has no parsed files, return None quietly."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[])
    client.create_chat = AsyncMock(
        side_effect=RuntimeError(
            "Ragflow API error 102: The dataset abc123 doesn't own parsed file"
        )
    )

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    result = await sync._ensure_chat_for_bot(
        bot_name="bot",
        dataset_id="abc123",
        llm_model_id=1,
        group_name="bot-document-index",
    )

    assert result is None
    sync._write_link.assert_not_awaited()


# ---------------------------------------------------------------------------
# Chat ownership and reconcile tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prefers_owned_chat(monkeypatch):
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")
    monkeypatch.setenv("RAGFLOW_TENANT_ID", "tenant-123")

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[
        {"id": "chat-old", "name": "bot-chat", "permission": "other", "tenant_id": "other"},
        {"id": "chat-owned", "name": "bot-chat", "permission": "me", "tenant_id": "tenant-123"},
    ])

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    chat_id = await sync._ensure_chat_for_bot(bot_name="bot", dataset_id="ds-1", llm_model_id=1, group_name="bot-document-index")

    assert chat_id == "chat-owned"


@pytest.mark.asyncio
async def test_does_not_reuse_unowned_chat(monkeypatch):
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")
    monkeypatch.setenv("RAGFLOW_TENANT_ID", "tenant-123")

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[
        {"id": "chat-other", "name": "bot", "permission": "other", "tenant_id": "other"},
    ])
    client.create_chat = AsyncMock(return_value={"id": "chat-created", "name": "bot"})

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()
    sync._resolve_ragflow_model_name = AsyncMock(return_value=None)

    chat_id = await sync._ensure_chat_for_bot(
        bot_name="bot",
        dataset_id="ds-1",
        llm_model_id=1,
        group_name="bot-document-index",
    )

    assert chat_id == "chat-created"
    client.create_chat.assert_awaited_once()
    sync._write_link.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_writes_missing_links(monkeypatch):
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[{"id": "ds-1", "name": "group-a"}])
    client.list_chats = AsyncMock(return_value=[{"id": "chat-1", "name": "group-a"}])

    pool = AsyncMock()
    mysql_api = AsyncMock()
    group = AsyncMock()
    group.name = "group-a"
    mysql_api.groups.retrieve = AsyncMock(return_value=group)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()
    sync._list_all_links = AsyncMock(return_value=[])

    res = await sync.reconcile_all_groups()

    assert res["datasets_linked"] == 1
    assert res["chats_linked"] == 1 or res["chats_linked"] == 0
    sync._write_link.assert_called()


@pytest.mark.asyncio
async def test_reconcile_clears_stale_dataset_link(monkeypatch):
    """When a Ragflow dataset is deleted, reconcile should remove the stale DB link."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[])
    client.list_chats = AsyncMock(return_value=[])

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()
    sync._delete_link = AsyncMock()
    sync._clear_stale_chat_link = AsyncMock()
    sync._list_all_links = AsyncMock(return_value=[
        {
            "group_name": "bot-document-index",
            "ragflow_dataset_id": "ds-deleted",
            "ragflow_dataset_name": "bot-document-index",
            "ragflow_chat_id": None,
            "updated_at": 0,
        }
    ])

    result = await sync.reconcile_all_groups()

    sync._delete_link.assert_awaited_once_with("bot-document-index")
    assert result["stale_links_cleared"] == 1


@pytest.mark.asyncio
async def test_reconcile_clears_stale_chat_link(monkeypatch):
    """When a Ragflow chat is deleted but dataset still exists, only chat_id is cleared."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[{"id": "ds-alive", "name": "bot-document-index"}])
    client.list_chats = AsyncMock(return_value=[])

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()
    sync._delete_link = AsyncMock()
    sync._clear_stale_chat_link = AsyncMock()
    sync._list_all_links = AsyncMock(return_value=[
        {
            "group_name": "bot-document-index",
            "ragflow_dataset_id": "ds-alive",
            "ragflow_dataset_name": "bot-document-index",
            "ragflow_chat_id": "chat-deleted",
            "updated_at": 0,
        }
    ])

    result = await sync.reconcile_all_groups()

    sync._clear_stale_chat_link.assert_awaited_once_with("bot-document-index")
    sync._delete_link.assert_not_awaited()
    assert result["stale_links_cleared"] == 1


# ── Vector 3: New edge-case hardening tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_ensure_chat_creates_unlinked_when_dataset_empty(monkeypatch) -> None:
    """When dataset has no parsed files, create_chat should be called with dataset_ids=[]."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[])
    # First call (with dataset_ids=[ds-1]) raises "parsed file" error; second call (with []) succeeds.
    client.create_chat = AsyncMock(
        side_effect=[
            RuntimeError("Ragflow API error 102: The dataset ds-1 doesn't own parsed file"),
            {"id": "chat-empty", "name": "my-bot"},
        ]
    )

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    chat_id = await sync._ensure_chat_for_bot(
        bot_name="my-bot",
        dataset_id="ds-1",
        llm_model_id=1,
        group_name="my-bot-document-index",
    )

    assert chat_id == "chat-empty"
    # Second call must use empty dataset_ids so Ragflow accepts it.
    second_call_kwargs = client.create_chat.call_args_list[1][1]
    assert second_call_kwargs.get("dataset_ids") == []


@pytest.mark.asyncio
async def test_ensure_chat_patches_existing_linked_chat(monkeypatch) -> None:
    """If the link already has a chat_id, patch_chat is called to update the dataset link."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.patch_chat = AsyncMock(return_value={})

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value={"ragflow_chat_id": "existing-chat-id"})
    sync._write_link = AsyncMock()

    result = await sync._ensure_chat_for_bot(
        bot_name="my-bot",
        dataset_id="new-ds-id",
        llm_model_id=1,
        group_name="my-bot-document-index",
    )

    assert result == "existing-chat-id"
    client.patch_chat.assert_awaited_once_with("existing-chat-id", dataset_ids=["new-ds-id"])


@pytest.mark.asyncio
async def test_sync_group_delete_graceful_on_404_chat(monkeypatch) -> None:
    """Delete cascade must remove local link even when Ragflow chat is already gone (404)."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.delete_chats = AsyncMock(
        side_effect=RuntimeError("Ragflow API error 404: not found")
    )
    client.delete_datasets = AsyncMock(return_value=None)
    # Wire _already_gone_error on the client instance.
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient
    client._already_gone_error = RagflowKbClient._already_gone_error

    pool = AsyncMock()
    mysql_api = AsyncMock()

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(
        return_value={
            "ragflow_dataset_id": "ds-1",
            "ragflow_chat_id": "chat-gone",
        }
    )
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="my-bot-document-index")

    # Local link must always be removed.
    sync._delete_link.assert_awaited_once_with("my-bot-document-index")
    # Dataset delete still attempted.
    client.delete_datasets.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_group_delete_graceful_on_404_dataset(monkeypatch) -> None:
    """Delete cascade removes local link even when Ragflow dataset is already gone."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.delete_chats = AsyncMock(return_value=None)
    client.delete_datasets = AsyncMock(
        side_effect=RuntimeError("Ragflow API error 102: doesn't exist")
    )
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient
    client._already_gone_error = RagflowKbClient._already_gone_error

    pool = AsyncMock()
    mysql_api = AsyncMock()

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(
        return_value={
            "ragflow_dataset_id": "ds-gone",
            "ragflow_chat_id": "chat-1",
        }
    )
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="my-bot-document-index")

    sync._delete_link.assert_awaited_once_with("my-bot-document-index")
    client.delete_chats.assert_awaited_once()


# ── Duplicate dataset/chat and delete reliability tests ──────────────────────

@pytest.mark.asyncio
async def test_sync_group_create_idempotent_on_duplicate_name(monkeypatch) -> None:
    """Creating the same group twice must not create duplicate Ragflow resources.
    The second call finds the existing dataset by name and reuses it.
    """
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    existing_dataset = {"id": "ds-existing", "name": "bot-document-index", "permission": "me"}

    client = AsyncMock()
    # First list returns empty (nothing exists yet), second returns existing
    client.list_datasets = AsyncMock(side_effect=[[], [existing_dataset]])
    client.create_dataset = AsyncMock(return_value={"id": "ds-new", "name": "bot-document-index"})
    client.list_chats = AsyncMock(return_value=[])
    client.create_chat = AsyncMock(return_value={"id": "chat-1", "name": "bot"})

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    config = GroupConfig(
        name="bot-document-index",
        type="DOCUMENT",
        llm_model_id=1,
        embedding_model_id=2,
        rerank_model_id=0,
    )

    # First create
    await sync.sync_group_create(config)
    first_create_count = client.create_dataset.await_count

    # Simulate second create call (as if Cria creates the same bot twice)
    sync._read_link = AsyncMock(return_value=None)
    client.list_datasets = AsyncMock(return_value=[existing_dataset])
    client.create_dataset = AsyncMock(return_value={"id": "ds-new-2", "name": "bot-document-index"})
    await sync.sync_group_create(config)

    # Second call must reuse the existing dataset — create_dataset NOT called again
    client.create_dataset.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_chat_no_duplicate_on_second_create(monkeypatch) -> None:
    """If a matching owned chat already exists in Ragflow, it must be reused — not duplicated."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    existing_chat = {"id": "chat-existing", "name": "my-bot", "permission": "me"}

    client = AsyncMock()
    client.list_chats = AsyncMock(return_value=[existing_chat])
    client.create_chat = AsyncMock(return_value={"id": "chat-new", "name": "my-bot"})
    client.patch_chat = AsyncMock(return_value={})

    pool = AsyncMock()
    mysql_api = AsyncMock()
    mysql_api.generic_models.retrieve = AsyncMock(return_value=None)

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._write_link = AsyncMock()

    chat_id = await sync._ensure_chat_for_bot(
        bot_name="my-bot",
        dataset_id="ds-1",
        llm_model_id=1,
        group_name="my-bot-document-index",
    )

    assert chat_id == "chat-existing"
    # Must NOT create a new chat when one already exists
    client.create_chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_group_delete_always_clears_link(monkeypatch) -> None:
    """Link must be cleared even when BOTH Ragflow chat and dataset deletions fail with 404."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = AsyncMock()
    client.delete_chats = AsyncMock(side_effect=RuntimeError("404 not found"))
    client.delete_datasets = AsyncMock(side_effect=RuntimeError("404 not found"))
    client._already_gone_error = RagflowKbClient._already_gone_error

    pool = AsyncMock()
    mysql_api = AsyncMock()

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(
        return_value={"ragflow_dataset_id": "ds-gone", "ragflow_chat_id": "chat-gone"}
    )
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="bot-document-index")

    sync._delete_link.assert_awaited_once_with("bot-document-index")


@pytest.mark.asyncio
async def test_sync_group_delete_runs_even_when_no_link(monkeypatch) -> None:
    """Delete with no link still sweeps owned datasets and chats by name."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[])
    client.list_chats = AsyncMock(return_value=[])
    client.delete_chats = AsyncMock()
    client.delete_datasets = AsyncMock()
    pool = AsyncMock()
    mysql_api = AsyncMock()

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value=None)
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="bot-document-index")

    client.list_datasets.assert_awaited()
    client.list_chats.assert_awaited()
    client.delete_chats.assert_not_awaited()
    client.delete_datasets.assert_not_awaited()
    sync._delete_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_chat_defers_link_when_parsing_in_progress(monkeypatch) -> None:
    """When patch_chat returns 102 'parsed file', a background retry task must be created."""
    import asyncio

    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    # First patch_chat fails with "parsed file", second succeeds (simulating parse completion)
    client.patch_chat = AsyncMock(
        side_effect=[
            RuntimeError("Ragflow API error 102: The dataset ds-1 doesn't own parsed file"),
            {},
        ]
    )

    pool = AsyncMock()
    mysql_api = AsyncMock()

    sync = RagflowKbSync(pool, mysql_api, client=client)
    sync._read_link = AsyncMock(return_value={"ragflow_chat_id": "chat-existing"})
    sync._write_link = AsyncMock()

    # Track whether retry task was created
    created_tasks = []
    original_create_task = asyncio.create_task

    def mock_create_task(coro, **kwargs):
        task = original_create_task(coro, **kwargs)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", mock_create_task)

    result = await sync._ensure_chat_for_bot(
        bot_name="my-bot",
        dataset_id="ds-1",
        llm_model_id=1,
        group_name="my-bot-document-index",
    )

    assert result == "chat-existing"
    # A background retry task must have been created
    assert len(created_tasks) >= 1


# _sync_chunks_to_es / list_chunks_for_document tests 

@pytest.mark.asyncio
async def test_sync_chunks_to_es_inserts_each_chunk(monkeypatch) -> None:
    """After Ragflow parsing, each chunk must be embedded and written to Elasticsearch."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    client = AsyncMock()
    client.list_chunks_for_document = AsyncMock(return_value=[
        {"content": "Learning objectives for week 1", "chunk_id": "c1"},
        {"content": "Assessment criteria and grading rubric", "chunk_id": "c2"},
    ])

    vector_store = AsyncMock()
    vector_store.ainsert = AsyncMock()
    vector_store.arefresh_collection = AsyncMock()

    embedder = AsyncMock()
    embedder.embed = MagicMock(side_effect=lambda text: [0.1, 0.2, 0.3])

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client, vector_store=vector_store, embedder=embedder)

    await sync._sync_chunks_to_es(
        group_name="bot-101-document-index",
        file_name="syllabus.html",
        dataset_id="dataset-99",
        document_ids=["doc-abc"],
    )

    client.list_chunks_for_document.assert_awaited_once_with("dataset-99", "doc-abc")
    assert vector_store.ainsert.await_count == 2

    first_call = vector_store.ainsert.await_args_list[0]
    assert first_call.kwargs["collection_name"] == "bot-101-document-index"
    assert first_call.kwargs["text"] == "Learning objectives for week 1"
    assert first_call.kwargs["metadata"]["file_name"] == "syllabus.html"


@pytest.mark.asyncio
async def test_sync_chunks_to_es_skips_empty_chunks(monkeypatch) -> None:
    """Whitespace-only chunks must not be embedded or inserted."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    client = AsyncMock()
    client.list_chunks_for_document = AsyncMock(return_value=[
        {"content": "   ", "chunk_id": "empty"},
        {"content": "Valid content here", "chunk_id": "c1"},
    ])

    vector_store = AsyncMock()
    vector_store.ainsert = AsyncMock()
    embedder = AsyncMock()
    embedder.embed = MagicMock(return_value=[0.1])

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client, vector_store=vector_store, embedder=embedder)

    await sync._sync_chunks_to_es(
        group_name="bot-document-index",
        file_name="doc.html",
        dataset_id="ds-1",
        document_ids=["doc-1"],
    )

    assert vector_store.ainsert.await_count == 1


@pytest.mark.asyncio
async def test_sync_chunks_to_es_noop_without_vector_store(monkeypatch) -> None:
    """When no vector_store is wired, the method exits immediately without hitting Ragflow."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    client = AsyncMock()

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client, vector_store=None, embedder=None)

    await sync._sync_chunks_to_es(
        group_name="bot-document-index",
        file_name="doc.html",
        dataset_id="ds-1",
        document_ids=["doc-1"],
    )

    client.list_chunks_for_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_chunks_to_es_tolerates_list_failure(monkeypatch) -> None:
    """A Ragflow chunk-list failure must be logged and swallowed, not propagated."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    client = AsyncMock()
    client.list_chunks_for_document = AsyncMock(side_effect=RuntimeError("Ragflow list_chunks_for_document failed: boom"))

    vector_store = AsyncMock()
    vector_store.ainsert = AsyncMock()
    embedder = AsyncMock()
    embedder.embed = MagicMock(return_value=[0.1])

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client, vector_store=vector_store, embedder=embedder)

    # Must not raise
    await sync._sync_chunks_to_es(
        group_name="bot-document-index",
        file_name="doc.html",
        dataset_id="ds-1",
        document_ids=["doc-1"],
    )

    vector_store.ainsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_native_file_upload_indexes_chunks_into_es(monkeypatch) -> None:
    """Full pipeline: upload → parse → pull chunks → insert into ES."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[])
    client.upload_document = AsyncMock(return_value=[{"id": "doc-1", "name": "page.txt"}])
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=True)
    client.list_chunks_for_document = AsyncMock(return_value=[
        {"content": "Course overview and objectives", "chunk_id": "c1"},
    ])

    vector_store = AsyncMock()
    vector_store.ainsert = AsyncMock()
    embedder = AsyncMock()
    embedder.embed = MagicMock(return_value=[0.5, 0.6])

    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(AsyncMock(), mysql_api, client=client, vector_store=vector_store, embedder=embedder)
    sync._ensure_dataset_for_group = AsyncMock(
        return_value={"ragflow_dataset_id": "dataset-1", "ragflow_dataset_name": "bot-document-index"}
    )
    sync._sync_chat_for_document_group = AsyncMock()

    await sync.sync_native_file_upload(
        group_name="bot-document-index",
        file_name="page.html",
        file_bytes=b"<html><body>Course overview</body></html>",
        strategy="PARAGRAPH",
        group_config=GroupConfig(
            name="bot-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        ),
    )

    client.parse_documents.assert_awaited_once_with("dataset-1", ["doc-1"])
    client.wait_for_documents_parsed.assert_awaited_once_with("dataset-1", ["doc-1"])
    client.list_chunks_for_document.assert_awaited_once_with("dataset-1", "doc-1")
    vector_store.ainsert.assert_awaited_once()

    insert_kwargs = vector_store.ainsert.await_args.kwargs
    assert insert_kwargs["collection_name"] == "bot-document-index"
    assert insert_kwargs["text"] == "Course overview and objectives"


@pytest.mark.asyncio
async def test_sync_native_file_upload_es_metadata_uses_original_filename(monkeypatch) -> None:
    """ES metadata file_name must match the MySQL record (original name, not post-parse .txt)
    so that delete_file()'s adelete_by_query(field='file_name') cleans up correctly."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[])
    client.upload_document = AsyncMock(return_value=[{"id": "doc-1", "name": "page.txt"}])
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=True)
    client.list_chunks_for_document = AsyncMock(return_value=[
        {"content": "Some content", "chunk_id": "c1"},
    ])

    vector_store = AsyncMock()
    vector_store.ainsert = AsyncMock()
    embedder = AsyncMock()
    embedder.embed = MagicMock(return_value=[0.1])

    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(AsyncMock(), mysql_api, client=client, vector_store=vector_store, embedder=embedder)
    sync._ensure_dataset_for_group = AsyncMock(
        return_value={"ragflow_dataset_id": "dataset-1", "ragflow_dataset_name": "bot-document-index"}
    )
    sync._sync_chat_for_document_group = AsyncMock()

    await sync.sync_native_file_upload(
        group_name="bot-document-index",
        file_name="learning_outcomes.html",  # original .html name stored in MySQL
        file_bytes=b"<html><body>Learning outcomes content</body></html>",
        strategy="PARAGRAPH",
        group_config=GroupConfig(
            name="bot-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        ),
    )

    insert_kwargs = vector_store.ainsert.await_args.kwargs
    # Must use the original .html name so delete_file() can clean up by file_name
    assert insert_kwargs["metadata"]["file_name"] == "learning_outcomes.html"


@pytest.mark.asyncio
async def test_sync_native_file_upload_skips_es_when_parse_times_out(monkeypatch) -> None:
    """If Ragflow parse times out, ES insertion must be skipped entirely."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[])
    client.upload_document = AsyncMock(return_value=[{"id": "doc-1", "name": "guide.txt"}])
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=False)  # timeout
    client.list_chunks_for_document = AsyncMock()

    vector_store = AsyncMock()
    vector_store.ainsert = AsyncMock()
    embedder = AsyncMock()
    embedder.embed = MagicMock(return_value=[0.1])

    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(AsyncMock(), mysql_api, client=client, vector_store=vector_store, embedder=embedder)
    sync._ensure_dataset_for_group = AsyncMock(
        return_value={"ragflow_dataset_id": "dataset-1", "ragflow_dataset_name": "bot-document-index"}
    )
    sync._sync_chat_for_document_group = AsyncMock()

    await sync.sync_native_file_upload(
        group_name="bot-document-index",
        file_name="guide.docx",
        file_bytes=b"binary docx content",
        strategy="ALSYLLABUS",
        group_config=GroupConfig(
            name="bot-document-index",
            type="DOCUMENT",
            llm_model_id=1,
            embedding_model_id=2,
            rerank_model_id=0,
        ),
    )

    client.list_chunks_for_document.assert_not_awaited()
    vector_store.ainsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_native_file_upload_schedules_es_retry_on_parse_timeout(monkeypatch) -> None:
    """When parse times out, sync_native_file_upload must schedule a background
    _retry_es_sync_after_parse task instead of silently dropping the ES sync."""
    import asyncio
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.list_documents = AsyncMock(return_value=[])
    client.upload_document = AsyncMock(return_value=[{"id": "doc-1", "name": "guide.txt"}])
    client.parse_documents = AsyncMock()
    client.wait_for_documents_parsed = AsyncMock(return_value=False)  # timeout

    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(AsyncMock(), mysql_api, client=client)
    sync._ensure_dataset_for_group = AsyncMock(
        return_value={"ragflow_dataset_id": "ds-1", "ragflow_dataset_name": "bot-document-index"}
    )
    sync._sync_chat_for_document_group = AsyncMock()

    retry_calls: list = []

    async def _fake_retry(**kwargs):
        retry_calls.append(kwargs)

    sync._retry_es_sync_after_parse = _fake_retry

    created_tasks: list = []
    original_create_task = asyncio.create_task

    def _patched_create_task(coro, **kwargs):
        created_tasks.append(coro)
        return original_create_task(coro, **kwargs)

    with patch("criadex.index.ragflow_objects.kb_sync.asyncio.create_task", _patched_create_task):
        await sync.sync_native_file_upload(
            group_name="bot-document-index",
            file_name="guide.docx",
            file_bytes=b"content",
            group_config=GroupConfig(
                name="bot-document-index",
                type="DOCUMENT",
                llm_model_id=1,
                embedding_model_id=2,
                rerank_model_id=0,
            ),
        )

    assert len(created_tasks) >= 1, "Expected a background task to be scheduled on parse timeout"


@pytest.mark.asyncio
async def test_retry_es_sync_calls_sync_chunks_when_documents_done(monkeypatch) -> None:
    """_retry_es_sync_after_parse must call _sync_chunks_to_es as soon as all
    target documents report run='DONE'."""
    import asyncio
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")

    client = AsyncMock()
    # First poll: still running; second poll: done
    client.list_documents = AsyncMock(
        side_effect=[
            [{"id": "doc-1", "name": "guide.txt", "run": "RUNNING"}],
            [{"id": "doc-1", "name": "guide.txt", "run": "DONE"}],
        ]
    )

    mysql_api = AsyncMock()
    mysql_api.groups.retrieve = AsyncMock(return_value=_mock_group_record(name="bot-document-index"))

    sync = RagflowKbSync(AsyncMock(), mysql_api, client=client)
    sync_calls: list = []

    async def _fake_sync_chunks(**kwargs):
        sync_calls.append(kwargs)

    sync._sync_chunks_to_es = _fake_sync_chunks

    with patch("asyncio.sleep", new=AsyncMock()):
        await sync._retry_es_sync_after_parse(
            group_name="bot-document-index",
            file_name="guide.docx",
            dataset_id="ds-1",
            document_ids=["doc-1"],
            retry_interval=0.0,
            max_attempts=5,
        )

    assert len(sync_calls) == 1
    assert sync_calls[0]["file_name"] == "guide.docx"
    assert sync_calls[0]["group_name"] == "bot-document-index"
    """list_chunks_for_document must paginate until a partial page is returned."""
    from unittest.mock import MagicMock
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    def _make_chunk(content: str):
        c = MagicMock()
        c.content = content
        c.id = f"chunk-{content[:4]}"
        return c

    page1 = [_make_chunk(f"chunk content {i}") for i in range(100)]
    page2 = [_make_chunk(f"page2 content {i}") for i in range(40)]

    mock_doc = MagicMock()
    mock_doc.list_chunks.side_effect = [page1, page2]

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()

    # Patch Document constructor to return our mock_doc
    with patch(
        "criadex.index.ragflow_objects.kb_client.Document",
        return_value=mock_doc,
    ):
        chunks = await client.list_chunks_for_document("dataset-1", "doc-1", page_size=100)

    assert len(chunks) == 140
    assert chunks[0]["content"] == "chunk content 0"
    assert chunks[100]["content"] == "page2 content 0"
    assert mock_doc.list_chunks.call_count == 2


@pytest.mark.asyncio
async def test_list_chunks_for_document_returns_empty_on_ragflow_error(monkeypatch) -> None:
    """A Ragflow SDK error in list_chunks must be wrapped and re-raised as RuntimeError."""
    from unittest.mock import MagicMock
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    mock_doc = MagicMock()
    mock_doc.list_chunks.side_effect = Exception("internal server error")

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()

    with patch(
        "criadex.index.ragflow_objects.kb_client.Document",
        return_value=mock_doc,
    ):
        with pytest.raises(RuntimeError, match="list_chunks_for_document failed"):
            await client.list_chunks_for_document("dataset-1", "doc-1")


# Chat ownership regression tests 

@pytest.mark.asyncio
async def test_chat_dict_includes_permission_and_tenant_id() -> None:
    """_chat_to_dict must expose permission and tenant_id so resource_is_owned()
    returns True for API-key-owned chats (permission='me') and the orphan sweep
    can delete them during group deletion."""
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._rag = MagicMock()
    chat_obj = _mock_chat_obj(id="chat-1", name="bot", dataset_ids=["ds-1"])
    chat_obj.permission = "me"
    chat_obj.tenant_id = "tenant-abc"
    client._rag.list_chats.return_value = [chat_obj]

    chats = await client.list_chats()

    assert len(chats) == 1
    assert chats[0]["permission"] == "me"
    assert chats[0]["tenant_id"] == "tenant-abc"


@pytest.mark.asyncio
async def test_sync_group_delete_cleans_orphan_chat_when_link_has_no_chat_id(monkeypatch) -> None:
    """When ragflow_chat_id is absent from the link (e.g. bot was created while the
    UnboundLocalError bug prevented chat linking), sync_group_delete must still find
    and delete the Ragflow chat via the name-based orphan sweep.

    Before the _chat_to_dict fix, resource_is_owned() always returned False for chats
    so the orphan sweep was a no-op and the chat persisted in the Ragflow web UI even
    after the Moodle course block was removed."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")

    client = AsyncMock()
    client.delete_datasets = AsyncMock()
    client.delete_chats = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[])
    client.list_chats = AsyncMock(return_value=[
        {"id": "orphan-chat", "name": "my-bot", "permission": "me", "tenant_id": None},
    ])
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient
    client._already_gone_error = RagflowKbClient._already_gone_error

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._read_link = AsyncMock(return_value={
        "group_name": "my-bot-document-index",
        "ragflow_dataset_id": "ds-1",
        "ragflow_dataset_name": "my-bot-document-index",
        "ragflow_chat_id": None,
    })
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="my-bot-document-index")

    # Dataset deleted by direct ID (no ownership check)
    client.delete_datasets.assert_awaited()
    deleted_dataset_ids = client.delete_datasets.await_args_list[0][0][0]
    assert "ds-1" in deleted_dataset_ids

    # Chat deleted via orphan sweep — this was the broken path before the fix
    client.delete_chats.assert_awaited()
    deleted_chat_ids = client.delete_chats.await_args_list[0][0][0]
    assert "orphan-chat" in deleted_chat_ids

    sync._delete_link.assert_awaited_once_with("my-bot-document-index")


@pytest.mark.asyncio
async def test_sync_group_delete_orphan_chat_sweep_skips_unowned(monkeypatch) -> None:
    """Orphan sweep must not delete Ragflow chats that aren't owned by this API key
    (permission != 'me' and no RAGFLOW_TENANT_ID match)."""
    monkeypatch.setenv("RAGFLOW_API_KEY", "test-key")
    monkeypatch.setenv("RAGFLOW_KB_SYNC_ENABLED", "true")
    monkeypatch.delenv("RAGFLOW_TENANT_ID", raising=False)

    client = AsyncMock()
    client.delete_chats = AsyncMock()
    client.delete_datasets = AsyncMock()
    client.list_datasets = AsyncMock(return_value=[])
    client.list_chats = AsyncMock(return_value=[
        {"id": "foreign-chat", "name": "my-bot", "permission": "team", "tenant_id": "other-tenant"},
    ])
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient
    client._already_gone_error = RagflowKbClient._already_gone_error

    sync = RagflowKbSync(AsyncMock(), AsyncMock(), client=client)
    sync._read_link = AsyncMock(return_value={
        "group_name": "my-bot-document-index",
        "ragflow_dataset_id": None,
        "ragflow_dataset_name": "my-bot-document-index",
        "ragflow_chat_id": None,
    })
    sync._delete_link = AsyncMock()

    await sync.sync_group_delete(group_name="my-bot-document-index")

    client.delete_chats.assert_not_awaited()
