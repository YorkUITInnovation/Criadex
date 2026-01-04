from fastapi import APIRouter
from pydantic import BaseModel
from criadex.agent.azure.language import LanguageAgent, LanguageAgentResponse

router = APIRouter()

class LanguageRequest(BaseModel):
    text: str

@router.post("/models/ragflow/{model_id}/agents/language")
async def ragflow_language(model_id: str, request: LanguageRequest) -> LanguageAgentResponse:
    agent = LanguageAgent()
    response = agent.detect(request.text)
    return response

