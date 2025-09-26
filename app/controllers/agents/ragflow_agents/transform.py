from fastapi import APIRouter
from criadex.index.ragflow_objects.transform import RagflowTransformAgentResponse, RagflowTransformAgent

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/transform")
def ragflow_transform(model_id: int):
    # Example stub: replace with actual RagflowTransformAgent logic
    return RagflowTransformAgentResponse(message="Ragflow transform stub", model_id=model_id)
