from fastapi import APIRouter
from criadex.index.ragflow_objects.related_prompts import RagflowRelatedPromptsGenerationAgent, RagflowRelatedPromptsGenerationAgentResponse
from criadex.schemas import AgentRelatedPromptsResponse, RelatedPromptsAgentResponse, CompletionUsage

router = APIRouter()

@router.post("/models/{model_id}/related_prompts")
def ragflow_related_prompts(model_id: int):
    return AgentRelatedPromptsResponse(
        agent_response=RelatedPromptsAgentResponse(
            related_prompts=[],
            usage=[
                CompletionUsage(completion_tokens=0, prompt_tokens=0, total_tokens=0, usage_label="RelatedPromptsAgent")
            ]
        )
    )
