from unittest.mock import AsyncMock

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
    model = AsyncMock()
    model.provider_type = "ragflow"
    model.config = {"api_model": "embed-english-v2.0"}
    mysql_api.generic_models.retrieve = AsyncMock(return_value=model)

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

    assert client.create_dataset.await_count == 2
    first_call = client.create_dataset.await_args_list[0].kwargs
    second_call = client.create_dataset.await_args_list[1].kwargs
    assert first_call.get("embedding_model") == "embed-english-v2.0"
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


@pytest.mark.asyncio
async def test_list_datasets_permission_error_treated_as_missing(monkeypatch) -> None:
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._request = AsyncMock(
        side_effect=RuntimeError(
            "Ragflow API error 108: User 'tenant' lacks permission for dataset 'missing'"
        )
    )

    datasets = await client.list_datasets(name="missing")
    assert datasets == []


@pytest.mark.asyncio
async def test_list_chats_missing_error_treated_as_empty(monkeypatch) -> None:
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._request = AsyncMock(
        side_effect=RuntimeError("Ragflow API error 102: The chat doesn't exist")
    )

    chats = await client.list_chats(name="missing-chat")
    assert chats == []


@pytest.mark.asyncio
async def test_list_chats_accepts_list_payload(monkeypatch) -> None:
    from criadex.index.ragflow_objects.kb_client import RagflowKbClient

    client = RagflowKbClient(api_key="test-key")
    client._request = AsyncMock(return_value={"code": 0, "data": [{"id": "chat-1", "name": "bot"}]})

    chats = await client.list_chats()
    assert chats == [{"id": "chat-1", "name": "bot"}]


@pytest.mark.asyncio
async def test_resolve_ragflow_model_name_appends_factory(monkeypatch) -> None:
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
    result = await sync._resolve_ragflow_model_name(42, model_kind="embedding")

    assert result == "embed-english-v2.0@Cohere"


@pytest.mark.asyncio
async def test_resolve_ragflow_model_name_no_double_at(monkeypatch) -> None:
    """If api_model already contains '@', do not append factory again."""
    pool = AsyncMock()
    mysql_api = AsyncMock()
    model = AsyncMock()
    model.provider_type = "ragflow"
    model.config = {
        "api_model": "embed-english-v2.0@Cohere",
        "llm_factory": "Cohere",
    }
    mysql_api.generic_models.retrieve = AsyncMock(return_value=model)

    sync = RagflowKbSync(pool, mysql_api)
    result = await sync._resolve_ragflow_model_name(42, model_kind="embedding")

    assert result == "embed-english-v2.0@Cohere"


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
