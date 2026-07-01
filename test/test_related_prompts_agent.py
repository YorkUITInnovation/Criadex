import pytest

from app.controllers.agents.ragflow_agents.related_prompts import (
    RelatedPromptsRequest,
    ragflow_related_prompts,
)
from criadex.index.ragflow_objects.chat import RagflowChatAgent


@pytest.mark.asyncio
async def test_related_prompts_without_chat_id_returns_empty_without_calling_ragflow(monkeypatch):
    called = False

    async def _chat(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should not be called without a chat_id")

    monkeypatch.setattr(RagflowChatAgent, "chat", _chat)

    response = await ragflow_related_prompts(
        model_id="1",
        request_body=RelatedPromptsRequest(llm_prompt="What is X?", llm_reply="X is Y."),
    )

    assert response.agent_response.related_prompts == []
    assert response.agent_response.usage == []
    assert called is False


@pytest.mark.asyncio
async def test_related_prompts_parses_ragflow_completion_into_prompts(monkeypatch):
    captured_kwargs = {}

    async def _chat(self, *, chat_id, history, api_key):
        captured_kwargs.update(chat_id=chat_id, history=history, api_key=api_key)
        return {
            "chat_response": {
                "message": {"blocks": [{"block_type": "text", "text": (
                    "1. How does X relate to Y?\n"
                    "- What are the limits of X?\n"
                    "Can I use X in production?\n"
                )}]}
            },
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }

    monkeypatch.setattr(RagflowChatAgent, "chat", _chat)

    response = await ragflow_related_prompts(
        model_id="1",
        request_body=RelatedPromptsRequest(
            llm_prompt="What is X?", llm_reply="X is Y.", chat_id="chat-42",
        ),
    )

    prompts = response.agent_response.related_prompts
    assert [p.prompt for p in prompts] == [
        "How does X relate to Y?",
        "What are the limits of X?",
        "Can I use X in production?",
    ]
    assert all(p.llm_generated for p in prompts)
    assert captured_kwargs["chat_id"] == "chat-42"

    usage = response.agent_response.usage
    assert len(usage) == 1
    assert usage[0].prompt_tokens == 5
    assert usage[0].completion_tokens == 10
    assert usage[0].total_tokens == 15
    assert usage[0].usage_label == "RelatedPromptsAgent"


@pytest.mark.asyncio
async def test_related_prompts_caps_at_three_even_with_more_lines(monkeypatch):
    async def _chat(self, *, chat_id, history, api_key):
        return {
            "chat_response": {"message": {"blocks": [{"block_type": "text", "text": (
                "Question one?\nQuestion two?\nQuestion three?\nQuestion four?\n"
            )}]}},
            "usage": {},
        }

    monkeypatch.setattr(RagflowChatAgent, "chat", _chat)

    response = await ragflow_related_prompts(
        model_id="1",
        request_body=RelatedPromptsRequest(llm_prompt="Q", llm_reply="A", chat_id="chat-1"),
    )

    assert len(response.agent_response.related_prompts) == 3


@pytest.mark.asyncio
async def test_related_prompts_falls_back_to_empty_on_ragflow_error(monkeypatch, caplog):
    async def _chat(self, *, chat_id, history, api_key):
        raise ValueError("Ragflow service is temporarily unavailable")

    monkeypatch.setattr(RagflowChatAgent, "chat", _chat)

    response = await ragflow_related_prompts(
        model_id="1",
        request_body=RelatedPromptsRequest(llm_prompt="Q", llm_reply="A", chat_id="chat-1"),
    )

    assert response.agent_response.related_prompts == []
    assert response.agent_response.usage == []
