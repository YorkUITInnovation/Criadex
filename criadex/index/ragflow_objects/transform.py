class RagflowTransformAgentResponse:
    def __init__(self, message: str, model_id: int):
        self.message = message
        self.model_id = model_id

class RagflowTransformAgent:
    def transform(self, model_id: int):
        return RagflowTransformAgentResponse(message=f"Transform for model {model_id}", model_id=model_id)
