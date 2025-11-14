from pydantic import BaseModel

class RagflowIntentsAgentResponse(BaseModel):
    message: str
    model_id: int


class RagflowIntentsAgent:
    def get_intents(self, model_id: int):
        return RagflowIntentsAgentResponse(message=f"Intents for model {model_id}", model_id=model_id)
