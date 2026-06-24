import uuid
import time
from unittest.mock import AsyncMock


def _fetch_link(client, headers, group_name):
    resp = client.get(f"/ragflow/link/{group_name}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == 200
    return data.get("stats")


def _wait_for_link(client, headers, group_name, timeout_seconds=3.0, require_chat=False):
    deadline = time.time() + timeout_seconds
    last_stats = None
    while time.time() < deadline:
        stats = _fetch_link(client, headers, group_name)
        last_stats = stats
        if stats and stats.get("ragflow_dataset_id"):
            if require_chat and not stats.get("ragflow_chat_id"):
                time.sleep(0.1)
                continue
            return stats
        time.sleep(0.1)
    return last_stats


def test_reconcile_endpoint_upserts_dataset_and_chat(client, sample_master_headers, monkeypatch):
    # Create a unique group name that will be matched by reconcile
    group_name = f"integration-bot-{uuid.uuid4()}-document-index"

    # Ensure group exists via API
    payload = {
        "type": "DOCUMENT",
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 0,
    }
    resp = client.post(f"/groups/{group_name}/create", headers=sample_master_headers, json=payload)
    assert resp.status_code in (200, 409)

    # Prepare fake Ragflow lists that include a dataset and chat with the same sanitized name
    fake_dataset = {"id": "ds-integ-1", "name": group_name}
    fake_chat = {"id": "ch-integ-1", "name": group_name}

    kb_sync = client.app.criadex.kb_sync
    # Monkeypatch Ragflow client list calls
    kb_sync._client.list_datasets = AsyncMock(return_value=[fake_dataset])
    kb_sync._client.list_chats = AsyncMock(return_value=[fake_chat])

    # Call reconcile endpoint
    resp = client.post('/ragflow/reconcile', headers=sample_master_headers)
    data = resp.json()

    assert data['status'] == 200
    # Stats always includes all keys
    assert "datasets_linked" in data['stats']
    assert "stale_links_cleared" in data['stats']

    # Now verify link was written through the API to avoid cross-loop DB access in tests
    link = _wait_for_link(client, sample_master_headers, group_name)
    assert link is not None
    assert link["ragflow_dataset_id"] == "ds-integ-1"

    # Chats may be linked as well depending on prior state
    # If not present, reconcile should have linked it because we returned a chat
    assert link.get("ragflow_chat_id") in (None, "ch-integ-1")


def test_document_upload_and_manual_sync_writes_links(client, sample_master_headers, monkeypatch):
    # Create a unique group and upload a small document, then assert link state via API.
    group_name = f"integration-upload-{uuid.uuid4()}-document-index"

    payload = {
        "type": "DOCUMENT",
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 0,
    }
    resp = client.post(f"/groups/{group_name}/create", headers=sample_master_headers, json=payload)
    assert resp.status_code in (200, 409)

    # Prepare kb_sync client to simulate upload/parse behavior
    kb_sync = client.app.criadex.kb_sync
    fake_dataset = {"id": "ds-upload-1", "name": group_name}

    # When ensuring dataset, return no existing datasets so create_dataset will be called
    kb_sync._client.list_datasets = AsyncMock(return_value=[])
    kb_sync._client.create_dataset = AsyncMock(return_value=fake_dataset)

    # Upload flow: no existing documents, upload returns an id and parse completes
    kb_sync._client.list_documents = AsyncMock(return_value=[])
    kb_sync._client.upload_document = AsyncMock(return_value=[{"id": "doc-1", "name": "readme.md"}])
    kb_sync._client.parse_documents = AsyncMock()
    kb_sync._client.wait_for_documents_parsed = AsyncMock(return_value=True)

    # Also prepare create_chat to succeed (chat creation will be attempted during sync)
    kb_sync._client.list_chats = AsyncMock(return_value=[])
    kb_sync._client.create_chat = AsyncMock(return_value={"id": "ch-upload-1", "name": group_name})

    # Upload document via API (this schedules kb_sync in background in the app loop).
    upload_payload = {
        "file_name": "readme.md",
        "file_contents": {"nodes": [{"text": "hello world"}]},
        "file_metadata": {"source": "unit-test"},
    }
    up_resp = client.post(f"/groups/{group_name}/content/upload", headers=sample_master_headers, json=upload_payload)
    assert up_resp.status_code == 200

    link = _wait_for_link(client, sample_master_headers, group_name, timeout_seconds=5.0, require_chat=True)
    assert link is not None
    assert link["ragflow_dataset_id"] == "ds-upload-1"
    # Chat created during document sync
    assert link.get("ragflow_chat_id") == "ch-upload-1"


def test_group_delete_cleans_ragflow_resources(client, sample_master_headers, monkeypatch):
    """Deleting a group via API must remove both remote Ragflow resources and local link."""
    group_name = f"integration-bot-{uuid.uuid4()}-document-index"

    payload = {
        "type": "DOCUMENT",
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 0,
    }
    resp = client.post(f"/groups/{group_name}/create", headers=sample_master_headers, json=payload)
    assert resp.status_code in (200, 409)

    # Inject a pre-existing link so delete has something to clean up.
    kb_sync = client.app.criadex.kb_sync
    kb_sync._client.delete_chats = AsyncMock(return_value=None)
    kb_sync._client.delete_datasets = AsyncMock(return_value=None)

    # Use existing list_* so sync_group_create doesn't race; simulate a link record.
    kb_sync._client.list_datasets = AsyncMock(
        return_value=[{"id": "ds-del-1", "name": group_name, "permission": "me"}]
    )
    kb_sync._client.list_chats = AsyncMock(return_value=[{"id": "ch-del-1", "name": group_name, "permission": "me"}])
    kb_sync._client.create_chat = AsyncMock(return_value={"id": "ch-del-1", "name": group_name})
    kb_sync._client.patch_chat = AsyncMock(return_value={})
    client.post("/ragflow/reconcile", headers=sample_master_headers)
    time.sleep(0.5)

    # Now delete the group.
    del_resp = client.delete(f"/groups/{group_name}/delete", headers=sample_master_headers)
    assert del_resp.status_code in (200, 204)

    # After background delete completes, link should be gone.
    time.sleep(1.0)
    link_after = _fetch_link(client, sample_master_headers, group_name)
    assert link_after is None or not link_after.get("ragflow_dataset_id")


def test_group_delete_graceful_when_ragflow_already_gone(client, sample_master_headers, monkeypatch):
    """Group delete must not fail when Ragflow resources are already 404 (idempotent)."""
    group_name = f"integration-bot-{uuid.uuid4()}-document-index"

    payload = {
        "type": "DOCUMENT",
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 0,
    }
    resp = client.post(f"/groups/{group_name}/create", headers=sample_master_headers, json=payload)
    assert resp.status_code in (200, 409)

    # Inject a link; Ragflow calls raise 404 as if resources already deleted.
    kb_sync = client.app.criadex.kb_sync
    kb_sync._client.delete_chats = AsyncMock(
        side_effect=RuntimeError("Ragflow API error 404: not found")
    )
    kb_sync._client.delete_datasets = AsyncMock(
        side_effect=RuntimeError("Ragflow API error 102: doesn't exist")
    )
    kb_sync._client.list_datasets = AsyncMock(
        return_value=[{"id": "ds-404-1", "name": group_name, "permission": "me"}]
    )
    kb_sync._client.list_chats = AsyncMock(return_value=[])
    client.post("/ragflow/reconcile", headers=sample_master_headers)
    time.sleep(0.5)

    del_resp = client.delete(f"/groups/{group_name}/delete", headers=sample_master_headers)
    assert del_resp.status_code in (200, 204)

    # Link should be cleared even though remote calls raised 404.
    time.sleep(1.0)
    link_after = _fetch_link(client, sample_master_headers, group_name)
    assert link_after is None or not link_after.get("ragflow_dataset_id")


def test_reconcile_clears_stale_dataset_link(client, sample_master_headers, monkeypatch):
    """Reconcile should detect a dataset deleted in Ragflow and clear the Criadex link."""
    group_name = f"integration-stale-{uuid.uuid4()}-document-index"

    payload = {
        "type": "DOCUMENT",
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 0,
    }
    resp = client.post(f"/groups/{group_name}/create", headers=sample_master_headers, json=payload)
    assert resp.status_code in (200, 409)

    kb_sync = client.app.criadex.kb_sync

    # Simulate that a link already exists for this group (as if previously synced)
    kb_sync._client.list_datasets = AsyncMock(
        return_value=[{"id": "ds-stale-1", "name": group_name, "permission": "me"}]
    )
    kb_sync._client.list_chats = AsyncMock(return_value=[])
    client.post("/ragflow/reconcile", headers=sample_master_headers)
    # Confirm link was written
    link = _wait_for_link(client, sample_master_headers, group_name)
    assert link and link.get("ragflow_dataset_id") == "ds-stale-1"

    # Now Ragflow no longer has that dataset (it was deleted externally)
    kb_sync._client.list_datasets = AsyncMock(return_value=[])
    kb_sync._client.list_chats = AsyncMock(return_value=[])

    resp = client.post("/ragflow/reconcile", headers=sample_master_headers)
    data = resp.json()
    assert data["status"] == 200
    assert data["stats"]["stale_links_cleared"] >= 1

    # Link should now be gone (or dataset_id cleared)
    time.sleep(0.5)
    link_after = _fetch_link(client, sample_master_headers, group_name)
    assert link_after is None or not link_after.get("ragflow_dataset_id")

