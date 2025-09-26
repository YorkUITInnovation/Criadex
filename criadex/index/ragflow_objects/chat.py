class RagflowChatAgentResponse:
    def __init__(self, message: str, model_id: int):
        self.message = message
        self.model_id = model_id

class RagflowChatAgent:
    def chat(self, model_id: int, query: str):
        return RagflowChatAgentResponse(message=f"Chat response for model {model_id}", model_id=model_id)
