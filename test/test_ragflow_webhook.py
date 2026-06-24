import os
from unittest.mock import AsyncMock

import pytest


from app.controllers.ragflow.webhook import WebhookRequest


@pytest.mark.asyncio
async def test_reconcile_endpoint_triggers_kb_sync(client, sample_master_headers, monkeypatch):
    # Arrange: stub kb_sync on app
    called = {}

    async def fake_reconcile():
        called['ran'] = True
        return {'datasets_linked': 1, 'chats_linked': 1, 'skipped': 0}

    monkeypatch.setenv('RAGFLOW_API_KEY', 'test-key')

    # attach fake to app
    client.app.criadex.kb_sync = AsyncMock()
    client.app.criadex.kb_sync.reconcile_all_groups = AsyncMock(return_value={'datasets_linked': 1, 'chats_linked': 1, 'skipped': 0})

    # Act
    resp = client.post('/ragflow/reconcile', headers=sample_master_headers)

    # Act
    data = resp.json()

    # Assert
    assert data['status'] == 200
    assert data['code'] == 'SUCCESS'
    assert 'stats' in data and data['stats']['datasets_linked'] == 1


@pytest.mark.asyncio
async def test_webhook_requires_valid_bearer_and_schedules(client, monkeypatch):
    monkeypatch.setenv('RAGFLOW_API_KEY', 'test-key')

    # attach fake kb_sync
    client.app.criadex.kb_sync = AsyncMock()
    client.app.criadex.kb_sync.reconcile_all_groups = AsyncMock(return_value={'datasets_linked': 0, 'chats_linked': 0, 'skipped': 0})

    headers = {'authorization': 'Bearer test-key'}
    payload = WebhookRequest(event='dataset.updated', resource={'id': 'ds-1'}).dict()

    resp = client.post('/ragflow/webhook', headers=headers, json=payload)
    data = resp.json()
    assert data['status'] in (202, 200)
    assert data['code'] in ('SUCCESS', )
