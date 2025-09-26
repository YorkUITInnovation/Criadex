from fastapi import APIRouter
from criadex.index.ragflow_objects.language import RagflowLanguageAgentResponse, RagflowLanguageAgent

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/language")
def ragflow_language(model_id: int):
    # Example stub: replace with actual RagflowLanguageAgent logic
    return RagflowLanguageAgentResponse(message="Ragflow language stub", model_id=model_id)
