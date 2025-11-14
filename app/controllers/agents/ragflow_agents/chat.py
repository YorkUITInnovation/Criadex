from fastapi import APIRouter, Body
from typing import List, Dict, Any, Optional
from criadex.agent.azure.chat import ChatAgent

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/chat")
async def chat_with_ragflow_model(
    model_id: int,
    agent_config: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Chat with a Ragflow model.
    """
    history = agent_config.get("history", [])
    if not history and "prompt" in agent_config:
        history = [{"role": "user", "content": agent_config["prompt"]}]

    agent = ChatAgent(llm_model_id=model_id)
    response = await agent.execute(history=history)
    return {"agent_response": response}
