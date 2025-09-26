from fastapi import APIRouter
from criadex.index.ragflow_objects.chat import RagflowChatAgentResponse, RagflowChatAgent

router = APIRouter()

@router.post("/models/ragflow/{model_id}/agents/chat")
def chat_with_ragflow_model(model_id: int):
    # Example stub: replace with actual RagflowChatAgent logic
    return RagflowChatAgentResponse(message="Chat with Ragflow model stub", model_id=model_id)
