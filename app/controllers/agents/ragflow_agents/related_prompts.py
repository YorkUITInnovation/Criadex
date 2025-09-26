from fastapi import APIRouter
from criadex.index.ragflow_objects.related_prompts import RagflowRelatedPromptsGenerationAgent, RagflowRelatedPromptsGenerationAgentResponse

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/related_prompts")
def ragflow_related_prompts(model_id: int):
    # Example stub: replace with actual RagflowRelatedPromptsGenerationAgent logic
    return RagflowRelatedPromptsGenerationAgentResponse(message="Ragflow related prompts stub", model_id=model_id)
