from fastapi import APIRouter
from criadex.agent.azure.intents import IntentsAgent, Intent
from pydantic import BaseModel
from typing import List

router = APIRouter()

class IntentsRequest(BaseModel):
    text: str
    intents: List[Intent] = []

@router.post("/models/ragflow/{model_id}/agents/intents")
async def ragflow_intents(model_id: str, request: IntentsRequest):
    agent = IntentsAgent(llm_model_id=model_id)
    response = await agent.execute(intents=request.intents, prompt=request.text)
    return {"agent_response": response}

