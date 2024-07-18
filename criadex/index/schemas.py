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

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Any, Optional

from llama_index.core import Document
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.indices.base import BaseIndex
from llama_index.core.ingestion import run_transformations
from llama_index.core.llms import LLM
from llama_index.core.schema import TextNode, NodeWithScore, TransformComponent
from pydantic import BaseModel, Field, ValidationError
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http.models import Filter

from criadex.index.llama_objects.extra_utils import TOKEN_COUNT_METADATA_KEY
from criadex.index.llama_objects.index_retriever import QdrantVectorIndexRetriever
from criadex.index.llama_objects.schemas import Reranker, CriadexFile


class CriadexBaseIndex(BaseIndex, ABC):
    """
    Overrides the base index from LlamaIndex to add custom functionality for Criadex

    """

    @classmethod
    @abstractmethod
    def seed_document(cls) -> CriadexFile:
        """
        Default seed file for the index (i.e. a seed value)

        :return: Default seed file created

        """

        raise NotImplementedError

    @abstractmethod
    def as_retriever(self, **kwargs: Any) -> QdrantVectorIndexRetriever:
        """
        Have to override retriever to add custom Qdrant functionality using drop-in class

        :param kwargs:
        :return:
        """
        raise NotImplementedError

    def insert(self, document: Document, **insert_kwargs: Any) -> int:
        """Insert a document."""

        with self._callback_manager.as_trace("insert"):
            nodes = run_transformations(
                [document],
                self._transformations,
                show_progress=self._show_progress,
            )

            self.insert_nodes(nodes, **insert_kwargs)
            self.docstore.set_document_hash(document.get_doc_id(), document.hash)

        return sum([node.metadata.get(TOKEN_COUNT_METADATA_KEY, 0) for node in nodes])


class MetaTextNode(TextNode):
    """
    A text node with metadata

    """

    metadata: dict = {}


class TextNodeWithScore(NodeWithScore):
    """
    A text node with a ranking score

    """

    node: MetaTextNode
    score: float


class IndexResponse(BaseModel):
    """
    Response from an index search

    """

    nodes: List[TextNodeWithScore]
    search_units: int = 1


class IndexTypeNotSupported(RuntimeError):
    """
    Thrown when an invalid index type is selected

    """


class IndexFileDataInvalidError(RuntimeError):
    """
    Invalid file data for this index

    """

    def __init__(self, issue: ValidationError, *args):
        super().__init__(*args)
        self.issue: ValidationError = issue


class QdrantConfig(BaseModel):
    """
    Config for storing in Qdrant

    """

    index_name: str
    qdrant_client: QdrantClient
    qdrant_aclient: AsyncQdrantClient

    class Config:
        arbitrary_types_allowed = True


class SearchConfig(BaseModel):
    """
    Configuration for searching an index

    """

    prompt: str

    # Vector DB
    top_k: int = Field(default=1, ge=1, le=1000)
    min_k: float = Field(default=0.5, ge=0.0, le=1.0)

    # Reranking
    top_n: int = Field(default=1, ge=1)
    min_n: float = Field(default=0.5, ge=0.0, le=1.0)

    rerank_enabled: bool = True
    search_filter: Optional[Filter] = None
    extra_groups: Optional[List[str]] = None


@dataclass()
class ServiceConfig:
    """
    Configuration dataclass for indexes

    """

    llm: Optional[LLM] = None
    embed_model: Optional[BaseEmbedding] = None
    rerank_model: Optional[Reranker] = None
    transformers: List[TransformComponent] = field(default_factory=list)
