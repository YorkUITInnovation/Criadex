class RagflowLLMAgentModelConfig:
    """
    Configuration for Ragflow LLM agent models.
    """
    def __init__(self, model_name: str = "default", temperature: float = 0.7, max_tokens: int = 2048):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def to_dict(self):
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
