from typing import List
from pydantic import BaseModel
from app.controllers.schemas import APIResponse, SUCCESS, ERROR, MODEL_NOT_FOUND

class CohereRerankRequest(BaseModel):
    query: str
    documents: List[dict]

class CohereRerankResponse(APIResponse):
    code: SUCCESS | MODEL_NOT_FOUND | ERROR
    reranked_documents: List[dict] | None = None