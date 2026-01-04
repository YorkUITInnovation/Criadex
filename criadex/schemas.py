"""

This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     Isaac Kogan
@copyright  2024 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later

"""
from enum import Enum
from typing import Optional, Type, Literal, cast, TypeVar, Callable, Awaitable, List
import time
import logging
import traceback
from functools import wraps

from pydantic import BaseModel, Field, ConfigDict


IndexTypeKeys: Type = Literal["DOCUMENT", "QUESTION"]


class IndexType(int, Enum):
    """
    The types of indexes as they map to MySQL ints & index classes

    """

    DOCUMENT = 1
    QUESTION = 2

    @property
    def value(self) -> int:
        """
        Return the value of the Enum as an int

        :return: Type-casted value

        """

        return cast(int, super().value)


class APIResponse(BaseModel):
    """
    Global API Response format that ALL responses must follow

    """

    status: int = 200
    message: Optional[str] = "Successfully completed the request!"
    timestamp: int = round(time.time())
    code: str = "SUCCESS"
    error: Optional[str] = Field(default=None, exclude=True)

    def dict(self, *args, **kwargs):

        self.message = self.message or {
            200: 'Request completed successfully!',
            409: 'The requested resource already exists!',
            400: 'You, the client, made a mistake...',
            500: 'An internal error occurred! :(',
            404: 'Womp womp. Not found!'
        }.get(self.status)

        data: dict = super().dict(*args, **kwargs)

        if "error" in data and data["error"] is None:
            del data["error"]

        return data

    model_config = ConfigDict(
        json_schema_extra=lambda schema, model: {
            "properties": {
                k: v for k, v in schema.get("properties", {}).items()
                if not v.get("hidden", v.get("exclude", None))
            }
        }
    )


APIResponseModel = TypeVar('APIResponseModel', bound=APIResponse)

UNAUTHORIZED: Type = Literal["UNAUTHORIZED"]
TIMEOUT: Type = Literal["TIMEOUT"]
ERROR: Type = Literal["ERROR"]
SUCCESS: Type = Literal["SUCCESS"]
NOT_FOUND: Type = Literal["NOT_FOUND"]
RATE_LIMIT: Type = Literal["RATE_LIMIT"]
DUPLICATE: Type = Literal["DUPLICATE"]
INVALID_INDEX_TYPE: Type = Literal["INVALID_INDEX_TYPE"]
GROUP_NOT_FOUND: Type = Literal["GROUP_NOT_FOUND"]
FILE_NOT_FOUND: Type = Literal["FILE_NOT_FOUND"]
INVALID_FILE_DATA: Type = Literal["INVALID_FILE_DATA"]
MODEL_IN_USE: Type = Literal["MODEL_IN_USE"]
MODEL_NOT_FOUND: Type = Literal["MODEL_NOT_FOUND"]
INVALID_MODEL: Type = Literal["INVALID_MODEL"]
INVALID_REQUEST: Type = Literal["INVALID_REQUEST"]
OPENAI_FILTER: Type = Literal["OPENAI_FILTER"]


class RateLimitResponse(APIResponse):
    status: int = 429
    code: RATE_LIMIT


class GroupExistsResponse(APIResponse):
    """
    Response for checking if a group exists.
    """
    exists: bool = Field(..., description="Whether the group exists.")


class UnauthorizedResponse(APIResponse):
    code: UNAUTHORIZED = "UNAUTHORIZED"
    status: int = 401
    detail: Optional[str]


class PartialGroupConfig(BaseModel):
    """
    Model representing the configuration of a NEW index group

    """

    type: IndexTypeKeys
    llm_model_id: int
    embedding_model_id: int
    rerank_model_id: int


class GroupConfig(PartialGroupConfig):
    """
    Model representing the configuration of an EXISTING index group

    """

    name: str


class MySQLCredentials(BaseModel):
    """
    Credentials for accessing the MySQL Database

    """

    host: str
    port: int
    username: str
    password: Optional[str] = None
    database: str


class ElasticsearchCredentials(BaseModel):
    """
    Model representing the credentials for accessing the Elasticsearch API

    """

    host: str
    port: int
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class IndexActivatedError(RuntimeError):
    """
    Thrown if the index is already activated

    """


class GroupExistsError(RuntimeError):
    """
    Thrown if the index group already exists and is being duplicated

    """


class GroupNotFoundError(RuntimeError):
    """
    Thrown if the index group does NOT exist and is being accessed

    """


class DocumentExistsError(RuntimeError):
    """
    Thrown if the document already exists in the index group and is being duplicated

    """


class ModelNotFoundError(RuntimeError):
    """
    Thrown if the model does not exist in the database and is being accessed

    """


class ModelExistsError(RuntimeError):
    """
    Thrown if the same deployment already exists in the database and is being duplicated

    """


class ModelInUseError(RuntimeError):
    """
    Thrown if trying to delete a model config while it's being used by an index

    """


class DocumentNotFoundError(RuntimeError):
    """
    Thrown if the document does not exist in the index group and is being accessed

    """


class EmptyPromptError(RuntimeError):
    """
    Thrown if the prompt is empty.

    """


class CompletionUsage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    usage_label: Optional[str] = None


class RelatedPrompt(BaseModel):
    label: str
    prompt: str
    llm_generated: bool = False


class BaseAgentResponse(BaseModel):
    message: Optional[str] = None


class LLMAgentResponse(BaseAgentResponse):
    usage: List[CompletionUsage]


class RelatedPromptsAgentResponse(LLMAgentResponse):
    related_prompts: List[RelatedPrompt]


class AgentRelatedPromptsResponse(BaseModel):
    agent_response: Optional[RelatedPromptsAgentResponse]

