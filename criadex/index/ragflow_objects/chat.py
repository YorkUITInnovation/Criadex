class RagflowChatAgent:
    def chat(self, model_id: int, query: str):
        # This is a stub implementation to match the expected response structure
        chat_message = {
            "role": "assistant",
            "blocks": [{"block_type": "text", "text": f"Chat response for model {model_id} and query: {query}"}],
            "additional_kwargs": {},
            "metadata": {}
        }

        chat_response = {
            "message": chat_message,
            "raw": {
                "id": "chatcmpl-stub",
                "choices": [],
                "created": 0,
                "model": f"ragflow-model-{model_id}",
                "object": "chat.completion",
                "system_fingerprint": None,
                "usage": {
                    "completion_tokens": 20,
                    "prompt_tokens": 10,
                    "total_tokens": 30
                }
            }
        }

        agent_response = {
            "chat_response": chat_response,
            "usage": [
                {
                    "completion_tokens": 20,
                    "prompt_tokens": 10,
                    "total_tokens": 30,
                    "usage_label": "stub"
                }
            ]
        }
        
        return agent_response
