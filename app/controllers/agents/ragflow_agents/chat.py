from fastapi import APIRouter, Body
from typing import List, Dict, Any, Optional

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/chat")
async def chat_with_ragflow_model(
    model_id: int,
    agent_config: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Stub for chatting with a Ragflow model.
    """
    prompt_text = "No prompt found"
    if agent_config.get("history"):
        for message in reversed(agent_config["history"]):
            if message.get("role") == "user" and message.get("blocks"):
                for block in message["blocks"]:
                    if block.get("block_type") == "text":
                        prompt_text = block.get("text")
                        break
                break

    chat_message = {
        "role": "assistant",
        "blocks": [{"block_type": "text", "text": f"This is a stubbed response for model {model_id} to the prompt: '{prompt_text}'"}],
        "additional_kwargs": {},
        "metadata": {}
    }

    chat_response = {
        "message": chat_message,
        "raw": {
            "id": "chatcmpl-stub",
            "choices": [],
            "created": 0,
            "model": f"ragflow-model-{model_id}",
            "object": "chat.completion",
            "system_fingerprint": None,
            "usage": {
                "completion_tokens": 20,
                "prompt_tokens": 10,
                "total_tokens": 30
            }
        }
    }

    agent_response = {
        "chat_response": chat_response,
        "usage": [
            {
                "completion_tokens": 20,
                "prompt_tokens": 10,
                "total_tokens": 30,
                "usage_label": "stub"
            }
        ]
    }

    return {"agent_response": agent_response}
