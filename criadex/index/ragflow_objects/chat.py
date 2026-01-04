import httpx
import json
import os
import logging
import hashlib
from datetime import datetime
import time

logger = logging.getLogger("uvicorn.error")

RAGFLOW_API_URL_TEMPLATE = os.getenv("RAGFLOW_API_URL_TEMPLATE", "http://ragflow:80/api/v1/chats_openai/{chat_id}/chat/completions")
RAGFLOW_DB_HOST = os.getenv("RAGFLOW_DB_HOST", "mysql")
RAGFLOW_DB_USER = os.getenv("RAGFLOW_DB_USER", "root")
RAGFLOW_DB_PASSWORD = os.getenv("RAGFLOW_DB_PASSWORD", "password")
RAGFLOW_DB_NAME = os.getenv("RAGFLOW_DB_NAME", "rag_flow")
RAGFLOW_TENANT_ID = os.getenv("RAGFLOW_TENANT_ID", "default_tenant")


class RagflowChatAgent:
    """
    Agent for communicating with Ragflow's OpenAI-compatible chat endpoint.
    Handles errors gracefully with proper logging and fallback responses.
    """

    async def ensure_dialog_exists(self, chat_id: str, tenant_id: str = None, llm_id: str = "gpt-3.5-turbo") -> bool:
        """
        Ensure a dialog exists in Ragflow for the given chat_id.
        If it doesn't exist, create it.

        :param chat_id: The chat session ID to ensure exists
        :param tenant_id: The tenant ID (defaults to RAGFLOW_TENANT_ID from env)
        :param llm_id: The LLM model to use for this dialog (defaults to gpt-3.5-turbo)
        :return: True if dialog exists or was created, False otherwise
        """
        if not tenant_id:
            tenant_id = RAGFLOW_TENANT_ID

        try:
            import aiomysql
            
            # Ragflow's dialog.id column is varchar(32), so hash the UUID to fit
            dialog_id = hashlib.md5(chat_id.encode()).hexdigest()[:32]
            
            # Connect to Ragflow database
            connection = await aiomysql.connect(
                host=RAGFLOW_DB_HOST,
                user=RAGFLOW_DB_USER,
                password=RAGFLOW_DB_PASSWORD,
                db=RAGFLOW_DB_NAME
            )
            cursor = await connection.cursor()

            # Check if dialog already exists
            check_query = "SELECT id FROM dialog WHERE id = %s AND tenant_id = %s LIMIT 1"
            await cursor.execute(check_query, (dialog_id, tenant_id))
            result = await cursor.fetchone()

            if result:
                logger.debug(f"Dialog {dialog_id} already exists for tenant {tenant_id}")
                await cursor.close()
                connection.close()
                return True

            # Dialog doesn't exist, create it
            now_ms = int(time.time() * 1000)
            now_dt = datetime.utcnow()

            insert_query = """
            INSERT INTO dialog (
                id, create_time, create_date, update_time, update_date, 
                tenant_id, name, description, language, llm_id, llm_setting, 
                prompt_type, prompt_config, similarity_threshold, 
                vector_similarity_weight, top_n, top_k, do_refer, rerank_id, 
                kb_ids, status
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            )
            """

            values = (
                dialog_id,                         # id (hashed to fit varchar(32))
                now_ms,                            # create_time
                now_dt,                            # create_date
                now_ms,                            # update_time
                now_dt,                            # update_date
                tenant_id,                         # tenant_id
                f"chat-{chat_id[:12]}",           # name (auto-generated)
                f"Auto-created chat session",      # description
                "English",                         # language
                llm_id,                            # llm_id
                "{}",                              # llm_setting (empty JSON)
                "simple",                          # prompt_type
                '{"prologue":"Hi"}',               # prompt_config
                0.2,                               # similarity_threshold
                0.3,                               # vector_similarity_weight
                6,                                 # top_n
                1024,                              # top_k
                "1",                               # do_refer
                "",                                # rerank_id
                "[]",                              # kb_ids (empty array)
                "1"                                # status (1=active)
            )

            await cursor.execute(insert_query, values)
            await connection.commit()
            logger.info(f"Successfully created dialog {dialog_id} for tenant {tenant_id}")
            await cursor.close()
            connection.close()
            return True

        except Exception as e:
            logger.error(f"Failed to ensure dialog exists for {chat_id}: {str(e)}", exc_info=True)
            return False

    async def chat(self, chat_id: str, history: list, api_key: str):
        """
        Send a chat request to Ragflow and get a response.

        :param chat_id: The chat session ID in Ragflow
        :param history: Chat history as list of dicts with 'role' and 'content'/'blocks'
        :param api_key: API key for authentication
        :return: Response dict with chat_response and usage
        :raises ValueError: If response validation fails
        """
        if len(chat_id) == 36:
            dialog_id = hashlib.md5(chat_id.encode()).hexdigest()[:32]
        else:
            dialog_id = chat_id
        url = RAGFLOW_API_URL_TEMPLATE.format(chat_id=dialog_id)

        headers = {}
        # Use standard Bearer token format expected by Ragflow's SDK-style
        # endpoints (e.g. those decorated with @token_required).
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Normalize messages from various formats
        messages = self._normalize_history(history)

        payload = {
            "model": "ragflow",
            "messages": messages,
            "stream": False
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                ragflow_response = response.json()

            # Validate response structure
            if "choices" not in ragflow_response or not ragflow_response["choices"]:
                error_message = ragflow_response.get("message", "Invalid response from Ragflow API")
                logger.error(f"Ragflow API error: 'choices' key missing or empty. Message: {error_message}")
                logger.error(f"Ragflow API raw response: {ragflow_response}")
                raise ValueError(error_message)

            # Extract response content
            assistant_content = ragflow_response["choices"][0]["message"]["content"]

            # Build standardized response
            chat_message = {
                "role": "assistant",
                "blocks": [{"block_type": "text", "text": assistant_content}],
                "additional_kwargs": {},
                "metadata": {}
            }

            chat_response = {
                "message": chat_message,
                "raw": ragflow_response
            }

            agent_response = {
                "chat_response": chat_response,
                "usage": ragflow_response.get("usage", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                })
            }

            return agent_response

        except httpx.ConnectError as e:
            error_message = f"Connection to Ragflow API failed at {url}"
            logger.error(f"Ragflow connection error: {error_message}")
            logger.error(f"Underlying error: {e}", exc_info=True)
            raise ValueError(error_message)

        except httpx.HTTPStatusError as e:
            error_message = f"Ragflow API returned error {e.response.status_code}: {e.response.reason_phrase}"
            logger.error(f"Ragflow HTTP error: {error_message}")
            try:
                raw_response = e.response.json()
                logger.error(f"Ragflow API response: {raw_response}")
                # Extract more specific error message if available
                if isinstance(raw_response, dict) and "message" in raw_response:
                    error_message = raw_response["message"]
            except json.JSONDecodeError:
                raw_response = e.response.text
                logger.error(f"Ragflow API response (not JSON): {raw_response}")

            raise ValueError(error_message)

        except (httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            error_message = f"Unexpected error calling Ragflow API: {str(e)}"
            logger.error(error_message, exc_info=True)
            raise ValueError(error_message)

    def _normalize_history(self, history: list) -> list:
        """
        Convert various chat history formats to OpenAI-compatible format.

        :param history: Chat history in various formats
        :return: List of dicts with 'role' and 'content' keys
        """
        messages = []
        for msg in history:
            if isinstance(msg, dict):
                # Handle blocks format (criabot format)
                if 'blocks' in msg and msg['blocks'] and isinstance(msg['blocks'], list):
                    content = msg['blocks'][0].get('text', '')
                    if content:
                        messages.append({"role": msg.get('role', 'user'), "content": content})
                # Handle direct content format (OpenAI format)
                elif 'content' in msg:
                    messages.append({"role": msg.get('role', 'user'), "content": msg.get('content')})
                # Handle message format (generic)
                elif 'message' in msg:
                    messages.append({"role": msg.get('role', 'user'), "content": msg.get('message', '')})

        return messages

