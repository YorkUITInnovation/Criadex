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

import asyncio
import functools
import time
import typing
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import List, Any, Optional, Sequence, TypeVar, Generic, Awaitable


from pydantic import BaseModel, Field
from criadex.database.tables.assets import AssetsModel
from criadex.database.tables.groups import GroupsModel
from criadex.index.ragflow_objects.schemas import RagflowDocument, RagflowTransformComponent, RagflowBaseNode, RagflowIndexNode, TOKEN_COUNT_METADATA_KEY, FILE_GROUP_META_STR, FILE_NAME_META_STR, FILE_CREATED_AT_META_STR, FILE_GROUP_ID_META_STR, RagflowReranker
from criadex.schemas import IndexType

if typing.TYPE_CHECKING:
    from criadex.index.index_api.document.index_objects import Element, DocumentConfig


class CriadexBaseIndex:
    """
    Overrides the base index from LlamaIndex to add custom functionality for Criadex

    """


    def __init__(self, **kwargs: Any):
        # Initialize Ragflow/Elasticsearch index here
        pass

    @classmethod
    @abstractmethod
    def seed_bundle(cls) -> Bundle:
        """
        Default seed file for the index (i.e. a seed value)

        :return: Default seed file created

        """

        raise NotImplementedError

    @classmethod
    async def run_transformations(
        cls,
        documents: List[RagflowDocument],
        transformations: List[RagflowTransformComponent],
        **kwargs: Any
    ) -> List[RagflowBaseNode]:
        """
        Run transformations on a list of documents

        :param documents: The documents to run transformations on
        :param transformations: The transformations to run
        :param kwargs: Options
        :return: The transformed nodes

        """

        # Some transformations from 3rd-party libs are sync ._.
        # Replace with Ragflow transformation logic
        return []

    async def initialize_index_struct(
        self,
        nodes: Sequence[RagflowBaseNode],
        **insert_kwargs: Any,
    ) -> dict:
        """Build index from nodes."""

        tasks = [
            self._async_add_nodes_to_index(
                self.index_struct,
                nodes,
                show_progress=self._show_progress,
                **insert_kwargs,
            )
        ]
        await asyncio.gather(*tasks)
        return self.index_struct

    def build_index_from_nodes(
            self,
            nodes: Sequence[RagflowBaseNode],
            **insert_kwargs: Any,
    ) -> dict:
        # Synchronous build not supported; use async_build_index_from_nodes instead
        raise NotImplementedError("Must use async methods implemented here instead!")

    async def async_build_index_from_nodes(
            self,
            nodes: Sequence[RagflowBaseNode],
            **insert_kwargs: Any,
    ) -> dict:
        """
        Build the index from nodes.
        """
        # Implement Ragflow async build logic here
        return {}

    async def insert_document(self, document: RagflowDocument, **insert_kwargs: Any) -> int:
        """Insert a document."""

        # Implement Ragflow document insertion logic
        return 0

    async def insert_document_nodes(self, nodes: Sequence[RagflowBaseNode], **insert_kwargs: Any) -> None:
        """
        Insert nodes.

        NOTE: overrides BaseIndex.insert_nodes.
            VectorStoreIndex only stores nodes in document store
            if vector store does not store text
        """

        # Implement Ragflow node insertion logic
        pass

    @classmethod
    async def from_store(
        cls,
        collection_name: str,
        service_config: ServiceConfig,
        storage_context: dict,
        **kwargs
    ) -> CriadexBaseIndex:
        """
        Load context FROM the vector store

        :param collection_name: The ID of the collection_name
        :param service_config: the index group service config
        :param storage_context: the index group storage context
        :param kwargs: Options
        :return: An instance of the loaded index

        """

        # Implement Ragflow/Elasticsearch index loading logic
        instance = cls()
        await instance.initialize_index_struct(nodes=[], **kwargs)
        return instance

    @classmethod
    async def from_scratch(
        cls,
        collection_name: str,
        service_config: ServiceConfig,
        storage_context: dict,
        **kwargs
    ) -> CriadexBaseIndex:
        """
        Create an index from scratch with defaults

        :param collection_name: The name of the collection
        :param service_config: the index group service context
        :param storage_context: the index group storage context
        :param kwargs: Options
        :return: An instance of the index group

        """

        # Implement Ragflow/Elasticsearch index creation logic
        instance = cls()
        await instance.initialize_index_struct(nodes=[], **kwargs)
        return instance

    def delete_nodes(self, node_ids: List[str], delete_from_docstore: bool = False, **delete_kwargs: Any) -> None:
        """
        Not used for this class

        :param node_ids: N/A
        :param delete_from_docstore: N/A
        :param delete_kwargs: N/A
        :return: N/A

        """

        return

    def as_retriever(self, **kwargs: Any):
        # Implement Ragflow retriever logic
        pass


class NodeLite(BaseModel):
    text: typing.Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class IndexResponse(BaseModel):
    """
    Response from an index search

    """

    nodes: List[NodeLite]
    assets: List[AssetsModel] = Field(default_factory=list)
    search_units: int = 1


class IndexTypeNotSupported(RuntimeError):
    """
    Thrown when an invalid index type is selected

    """


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
    # Generic filter object applied at the application layer for Elasticsearch
    search_filter: Optional[dict] = None
    extra_groups: Optional[List[str]] = None



@dataclass()
class ServiceConfig:
    """
    Configuration dataclass for indexes
    """
    llm: Optional[object] = None
    embed_model: Optional[object] = None
    rerank_model: Optional[RagflowReranker] = None
    transformers: List[object] = field(default_factory=list)


class RawAsset(BaseModel):
    uuid: str  # Must not be generated. Must be passed from whatever the element_id was
    data_mimetype: str
    data_base64: str
    description: str


class EmptyDocumentConfig(RuntimeError):
    """
    Exception for when an empty file is provided to Bundle

    """


BundleConfig = TypeVar("BundleConfig", bound=BaseModel)


class Bundle(BaseModel, Generic[BundleConfig]):
    name: str
    config: BundleConfig
    group: GroupsModel
    metadata: dict = Field(default_factory=dict)

    def to_document(self) -> RagflowDocument:
        """Convert a Bundle to a RagflowDocument"""
        if not self.config:
            raise EmptyDocumentConfig("No config provided!")
        metadata: dict = {
            **self.metadata,
            FILE_GROUP_META_STR: self.group.name,
            FILE_NAME_META_STR: self.name,
            FILE_CREATED_AT_META_STR: round(time.time()),
            FILE_GROUP_ID_META_STR: self.group.id
        }
        # Default behaviour is to exclude all keys
        excluded_llm_keys: List[str] = []
        excluded_embed_keys: List[str] = ['image_base64']
        # Create a RagflowDocument
        return RagflowDocument(
            text=self.config.model_dump_json(),
            doc_id=self.name,
            metadata=metadata,
            collection_name=self.group.name, # Add collection_name here
            excluded_llm_metadata_keys=excluded_llm_keys,
            excluded_embed_metadata_keys=excluded_embed_keys
        )

    def pop_assets(self) -> list[RawAsset]:

        # Assets are only implemented on DocumentConfig
        if self.group.type != IndexType.DOCUMENT.value:
            return []

        # Do not copy, must be able to pop from the original
        config: DocumentConfig = self.config

        # Backwards compatibility for old Cria frontend versions
        # Feb 5, 2025, Patrick is away. To add immediate support for assets,
        # I have added 'ENABLE_BACKWARDS_COMPATIBLE_ASSET_CONTAINER' as a TEMPORARY << read: TEMPORARY!!!! solution.
        # This passed an additional 'meta' element Criadex extracts when uploading a document.
        if len(config.nodes) > 0 and config.nodes[-1].type.value == "BackwardsCompatibleAssetContainer":
            last_node: Element = config.nodes.pop(-1)
            return [RawAsset(**asset_dict) for asset_dict in last_node.metadata.get('assets')]

        return config.assets

    @classmethod
    def _get_excluded_keys(cls, metadata: dict, *allowed_keys: str) -> List[str]:
        """
        The keys to exclude from being added into the node text

        :param metadata: The metadata object
        :param allowed_keys: The keys to allow
        :return: The keys to exclude

        """

        excluded_keys: List[str] = []

        for key in metadata.keys():

            # Allowed keys are always included
            if key in allowed_keys:
                continue

            # Include common metadata keys for searching
            if key in (FILE_NAME_META_STR, FILE_GROUP_META_STR, FILE_CREATED_AT_META_STR, FILE_GROUP_ID_META_STR):
                continue

            excluded_keys.append(key)

        return excluded_keys
