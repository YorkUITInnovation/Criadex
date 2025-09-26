from fastapi import APIRouter
from criadex.index.ragflow_objects.intents import RagflowIntentsAgent, RagflowIntentsAgentResponse

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/intents")
def ragflow_intents(model_id: int):
    # Example stub: replace with actual RagflowIntentsAgent logic
    return RagflowIntentsAgentResponse(message="Ragflow intents stub", model_id=model_id)
