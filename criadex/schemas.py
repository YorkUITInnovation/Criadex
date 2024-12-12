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
from typing import Optional, Type, Literal, cast

from pydantic import BaseModel

from criadex.index.base_api import CriadexIndexAPI
from .index.index_api.document.index import DocumentIndexAPI
from .index.index_api.question.index import QuestionIndexAPI

IndexTypeKeys: Type = Literal["DOCUMENT", "QUESTION"]


class IndexType(int, Enum):
    """
    The types of indexes as they map to MySQL ints & index classes

    """

    DOCUMENT = 1
    QUESTION = 2

    @classmethod
    def to_index(cls, type_id: int) -> Optional[CriadexIndexAPI]:
        """
        Map a given MySQL type ID to its respective class

        :param type_id: The ID of the type (its number)
        :return: The associated index

        """

        return (
            {
                cls.DOCUMENT.value: DocumentIndexAPI,
                cls.QUESTION.value: QuestionIndexAPI,
            }
        ).get(type_id, None)

    @property
    def value(self) -> int:
        """
        Return the value of the Enum as an int

        :return: Type-casted value

        """

        return cast(int, super().value)


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


class QdrantCredentials(BaseModel):
    """
    Model representing the credentials for accessing the Qdrant API

    """

    host: str
    port: int
    grpc_port: int
    api_key: Optional[str] = None


class MySQLCredentials(BaseModel):
    """
    Credentials for accessing the MySQL Database

    """

    host: str
    port: int
    username: str
    password: Optional[str] = None
    database: str


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


