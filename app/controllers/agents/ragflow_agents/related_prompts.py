import logging
import os
import re
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from criadex.index.ragflow_objects.chat import RagflowChatAgent
from criadex.schemas import AgentRelatedPromptsResponse, CompletionUsage, RelatedPrompt, RelatedPromptsAgentResponse

router = APIRouter()

logger = logging.getLogger("uvicorn.error")

_LEADING_MARKER_RE = re.compile(r"^[\-\*•]\s*|^\d+[.)]?\s*")


class RelatedPromptsRequest(BaseModel):
    llm_prompt: str
    llm_reply: str
    chat_id: Optional[str] = None
    max_reply_tokens: int = 500
    temperature: float = 0.1


def _parse_related_prompts(text: str, limit: int = 3) -> List[RelatedPrompt]:
    prompts: List[RelatedPrompt] = []
    for line in (text or "").splitlines():
        cleaned = _LEADING_MARKER_RE.sub("", line.strip()).strip()
        if not cleaned:
            continue
        prompts.append(RelatedPrompt(label=cleaned[:60], prompt=cleaned, llm_generated=True))
        if len(prompts) >= limit:
            break
    return prompts


def _empty_response() -> AgentRelatedPromptsResponse:
    return AgentRelatedPromptsResponse(
        agent_response=RelatedPromptsAgentResponse(related_prompts=[], usage=[])
    )


@router.post("/models/{model_id}/related_prompts")
async def ragflow_related_prompts(model_id: str, request_body: RelatedPromptsRequest) -> AgentRelatedPromptsResponse:
    """
    Ask the bot's own Ragflow dialog to suggest follow-up questions, reusing the
    same chat completion path as a real reply (RagflowChatAgent.chat) — no
    separate "related prompts" model/API exists in Ragflow.
    """
    if not request_body.chat_id:
        return _empty_response()

    instruction = (
        f"Question: {request_body.llm_prompt}\n"
        f"Answer: {request_body.llm_reply}\n\n"
        "Suggest 3 short, distinct follow-up questions the user might ask next. "
        "Reply with ONLY the questions, one per line, no numbering or extra text."
    )

    try:
        agent_response = await RagflowChatAgent().chat(
            chat_id=request_body.chat_id,
            history=[{"role": "user", "content": instruction}],
            api_key=os.getenv("RAGFLOW_API_KEY", ""),
        )
        text = agent_response["chat_response"]["message"]["blocks"][0]["text"]
        related_prompts = _parse_related_prompts(text)
        usage = agent_response.get("usage") or {}

        return AgentRelatedPromptsResponse(
            agent_response=RelatedPromptsAgentResponse(
                related_prompts=related_prompts,
                usage=[CompletionUsage(
                    completion_tokens=usage.get("completion_tokens", 0),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    usage_label="RelatedPromptsAgent",
                )] if usage else [],
            )
        )
    except Exception:
        logger.warning(
            "Failed to generate related prompts for chat_id=%s", request_body.chat_id, exc_info=True
        )
        return _empty_response()
