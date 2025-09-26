class RagflowRelatedPromptsGenerationAgentResponse:
    def __init__(self, message: str, model_id: int):
        self.message = message
        self.model_id = model_id

class RagflowRelatedPromptsGenerationAgent:
    def generate_prompts(self, model_id: int):
        return RagflowRelatedPromptsGenerationAgentResponse(message=f"Related prompts for model {model_id}", model_id=model_id)
