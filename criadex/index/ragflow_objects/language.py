class RagflowLanguageAgentResponse:
    def __init__(self, message: str, model_id: int):
        self.message = message
        self.model_id = model_id

class RagflowLanguageAgent:
    def process_language(self, model_id: int):
        return RagflowLanguageAgentResponse(message=f"Language processed for model {model_id}", model_id=model_id)
