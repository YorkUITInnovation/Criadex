from unittest.mock import MagicMock

import httpx
import pytest

from app.controllers.agents.ragflow_agents.chat import ChatAgentRequest, RagflowChatRoute
from criadex.index.ragflow_objects.chat import RagflowChatAgent


class _TimeoutAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        raise httpx.ReadTimeout("timed out")


class _ResponseStub:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.reason_phrase = "Bad Request" if status_code >= 400 else "OK"
        self.request = httpx.Request("POST", "http://test.local")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request, json=self._payload),
            )

    def json(self):
        return self._payload


class _OwnershipRetryAsyncClient:
    calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.__class__.calls += 1
        if self.__class__.calls == 1:
            return _ResponseStub(400, {"code": 102, "message": "You don't own the chat deadbeef"})
        return _ResponseStub(200, {
            "choices": [{"message": {"content": "Recovered"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })


@pytest.mark.asyncio
async def test_ragflow_chat_agent_timeout_is_classified_without_error_stack(monkeypatch, caplog):
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _TimeoutAsyncClient())

    agent = RagflowChatAgent()

    with pytest.raises(ValueError, match="Ragflow API timed out"):
        await agent.chat(chat_id="chat-1", history=[{"role": "user", "content": "hi"}], api_key="key")

    assert "Ragflow API timeout" in caplog.text
    assert "Unexpected error calling Ragflow API" not in caplog.text


@pytest.mark.asyncio
async def test_ragflow_chat_route_maps_timeout_to_service_error(monkeypatch):
    async def _timeout(*args, **kwargs):
        raise ValueError("Ragflow API timed out")

    monkeypatch.setattr(RagflowChatAgent, "chat", _timeout)

    request_body = ChatAgentRequest(
        chat_id="chat-1",
        history=[],
        prompt="hello",
    )

    route = RagflowChatRoute()
    response = await route.execute(model_id="1", request_body=request_body, request=MagicMock())

    assert response.code == "ERROR"
    assert response.status == 502
    assert "temporarily unavailable" in response.message.lower()


@pytest.mark.asyncio
async def test_ragflow_chat_agent_recovers_from_chat_ownership_conflict(monkeypatch):
    _OwnershipRetryAsyncClient.calls = 0
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _OwnershipRetryAsyncClient())

    async def _ensure_dialog_exists(*args, **kwargs):
        return True

    monkeypatch.setattr(RagflowChatAgent, "ensure_dialog_exists", _ensure_dialog_exists)

    agent = RagflowChatAgent()
    response = await agent.chat(chat_id="chat-ownership", history=[{"role": "user", "content": "hi"}], api_key="key")

    assert response["chat_response"]["message"]["blocks"][0]["text"] == "Recovered"
    assert _OwnershipRetryAsyncClient.calls == 2
    assert "chat-ownership" in RagflowChatAgent._chat_aliases
