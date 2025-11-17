import httpx
import json

class RagflowChatAgent:
    async def chat(self, model_id: int, history: list):
        payload = {
            "model": f"ragflow-model-{model_id}",
            "messages": history
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post("http://ragflow:9380/v1/chat/completions", json=payload, timeout=30)
                response.raise_for_status()
                ragflow_response = response.json()

                if "choices" not in ragflow_response or not ragflow_response["choices"]:
                    print(f"Error calling Ragflow API: 'choices' key missing or empty in response")
                    print(f"Ragflow API raw response: {ragflow_response}")
                    # Fallback to a stubbed response
                    chat_message = {
                        "role": "assistant",
                        "blocks": [{"block_type": "text", "text": "Error: Invalid response from Ragflow API."}],
                        "additional_kwargs": {},
                        "metadata": {}
                    }
                    chat_response = {"message": chat_message, "raw": ragflow_response}
                    agent_response = {
                        "chat_response": chat_response,
                        "usage": {
                            "completion_tokens": 0,
                            "prompt_tokens": 0,
                            "total_tokens": 0,
                            "usage_label": "error"
                        }
                    }
                    return agent_response
                
                # Adapt the Ragflow response to the format expected by ChatAgent
                chat_message = {
                    "role": "assistant",
                    "blocks": [{"block_type": "text", "text": ragflow_response["choices"][0]["message"]["content"]}],
                    "additional_kwargs": {},
                    "metadata": {}
                }

                chat_response = {
                    "message": chat_message,
                    "raw": ragflow_response
                }

                agent_response = {
                    "chat_response": chat_response,
                    "usage": ragflow_response["usage"]
                }
                
                return agent_response

            except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, KeyError) as e:
                print(f"Error calling Ragflow API: {e}")
                if isinstance(e, httpx.HTTPStatusError) and e.response:
                    print(f"Ragflow API raw response: {e.response.text}")
                elif isinstance(e, httpx.RequestError):
                    print(f"Ragflow API request error: {e.request}")
                elif isinstance(e, json.JSONDecodeError):
                    print(f"Ragflow API JSON decode error: {e.doc}")
                elif isinstance(e, KeyError):
                    print(f"Ragflow API response missing key: {e}")
                # Fallback to a stubbed response in case of an error
                chat_message = {
                    "role": "assistant",
                    "blocks": [{"block_type": "text", "text": f"Error calling Ragflow: {e}"}],
                    "additional_kwargs": {},
                    "metadata": {}
                }
                chat_response = {"message": chat_message, "raw": {}}
                agent_response = {
                    "chat_response": chat_response,
                    "usage": {
                        "completion_tokens": 0,
                        "prompt_tokens": 0,
                        "total_tokens": 0,
                        "usage_label": "error"
                    }
                }
                return agent_response
