"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

 @package    Criadex
 @author     Kiarash Bashokian
 @copyright  2024 onwards York University (https://yorku.ca/)
 @repository https://github.com/YorkUITInnovation/Criadex
 @license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter
import os
import logging
from pydantic import BaseModel
from starlette.requests import Request
from fastapi_restful.cbv import cbv

from criadex.index.ragflow_objects.chat import RagflowChatAgent
from app.core.route import CriaRoute

router = APIRouter()

logger = logging.getLogger("uvicorn.error")


class ChatMessage(BaseModel):
    """Chat message model supporting multiple formats"""
    role: str
    content: Optional[str] = None
    blocks: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


class ChatAgentRequest(BaseModel):
    history: List[ChatMessage] = []
    chat_id: str
    prompt: Optional[str] = None


class RagflowChatResponse(BaseModel):
    code: str
    status: int
    message: str
    agent_response: Optional[Dict[str, Any]] = None


@cbv(router)
class RagflowChatRoute(CriaRoute):
    ResponseModel = RagflowChatResponse

    @router.post("/models/ragflow/{model_id}/agents/chat")
    async def execute(
        self,
        model_id: str,
        request_body: ChatAgentRequest,
        request: Request
    ) -> RagflowChatResponse:
        """
        Chat with a Ragflow model.
        Standard error handling and response structure following Criadex patterns.
        """
        # Validate chat_id
        if not request_body.chat_id:
            return self.ResponseModel(
                code="INVALID_REQUEST",
                status=400,
                message="chat_id is required in the request configuration",
                agent_response=None
            )

        # Build history from config
        history = request_body.history if request_body.history else []
        if not history and request_body.prompt:
            history = [{"role": "user", "content": request_body.prompt}]

        # Convert Pydantic models to dicts for compatibility
        history_dicts = [h.dict() if hasattr(h, 'dict') else h for h in history]

        # Initialize agent and execute
        agent = RagflowChatAgent()
        try:
            # Use server-side RAGFLOW_API_KEY. Do not forward client keys.
            api_key = os.getenv("RAGFLOW_API_KEY", "")
            agent_response = await agent.chat(
                chat_id=request_body.chat_id,
                history=history_dicts,
                api_key=api_key
            )

            # Standard success response
            return self.ResponseModel(
                code="SUCCESS",
                status=200,
                message="Chat completed successfully",
                agent_response=agent_response
            )

        except ValueError as e:
            # Treat validation/authentication errors from Ragflow as upstream
            # service errors (502). Provide an actionable message for operators.
            msg = str(e)
            if "Authentication" in msg or "API key" in msg or "invalid" in msg.lower():
                return self.ResponseModel(
                    code="ERROR",
                    status=502,
                    message=(
                        "Ragflow authentication failed. "
                        "Ensure RAGFLOW_API_KEY is configured in the environment."
                    ),
                    agent_response=None
                )

            if "timed out" in msg.lower() or "temporarily unavailable" in msg.lower() or "connection to ragflow api failed" in msg.lower():
                return self.ResponseModel(
                    code="ERROR",
                    status=502,
                    message="Ragflow service is temporarily unavailable. Please try again later.",
                    agent_response=None
                )

            # Other validation errors map to bad request
            return self.ResponseModel(
                code="INVALID_REQUEST",
                status=400,
                message=f"Ragflow API validation error: {msg}",
                agent_response=None
            )

        except Exception as e:
            # Generic error handling with fallback response
            logger.error(f"Ragflow chat error: {str(e)}", exc_info=True)

            # Return error response with fallback message structure
            fallback_response = {
                "chat_response": {
                    "message": {
                        "role": "assistant",
                        "blocks": [{
                            "block_type": "text",
                            "text": f"Service temporarily unavailable. Please try again later."
                        }],
                        "additional_kwargs": {},
                        "metadata": {}
                    },
                    "raw": {}
                },
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

            return self.ResponseModel(
                code="ERROR",
                status=502,
                message="Error communicating with Ragflow service",
                agent_response=fallback_response
            )

