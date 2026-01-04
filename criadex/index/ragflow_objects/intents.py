from pydantic import BaseModel

class RagflowIntentsAgentResponse(BaseModel):
    message: str
    model_id: str


class RagflowIntentsAgent:
    def get_intents(self, model_id: str):
        return RagflowIntentsAgentResponse(message=f"Intents for model {model_id}", model_id=model_id)
