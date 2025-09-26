class RagflowIntentsAgentResponse:
    def __init__(self, message: str, model_id: int):
        self.message = message
        self.model_id = model_id

class RagflowIntentsAgent:
    def get_intents(self, model_id: int):
        return RagflowIntentsAgentResponse(message=f"Intents for model {model_id}", model_id=model_id)
