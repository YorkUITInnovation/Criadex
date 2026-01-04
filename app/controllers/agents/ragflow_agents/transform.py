from fastapi import APIRouter
from pydantic import BaseModel
from criadex.agent.azure.transform import TransformAgent, TransformAgentResponse

router = APIRouter()

class TransformRequest(BaseModel):
    text: str

@router.post("/models/ragflow/{model_id}/agents/transform")
async def ragflow_transform(model_id: str, request: TransformRequest) -> TransformAgentResponse:
    agent = TransformAgent()
    response = agent.transform(request.text)
    return response

