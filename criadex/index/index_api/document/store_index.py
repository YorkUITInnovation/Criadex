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

import asyncio
from typing import List, Any

from llama_index.core.indices import VectorStoreIndex
from llama_index.core.storage import StorageContext

from criadex.index.index_api.document.index_objects import DocumentConfig, Element, ElementType
from criadex.index.llama_objects.index_retriever import QdrantVectorIndexRetriever
from criadex.index.llama_objects.schemas import CriadexFile
from criadex.index.schemas import CriadexBaseIndex, ServiceConfig


class DocumentVectorStoreIndex(VectorStoreIndex, CriadexBaseIndex):
    """
    Index vector store for node-based documents

    """

    @classmethod
    def seed_document(cls) -> CriadexFile:
        """
        Create a seed document for a new index
        :return: The seed document

        """

        return CriadexFile.create(
            file_name="seed-file",
            text=DocumentConfig(nodes=[Element(type=ElementType.NARRATIVE_TEXT, text="seed-text")]).json(),
            file_group="seed-group",
            file_metadata=dict()
        )

    @classmethod
    async def from_store(
            cls,
            collection_name: str,
            service_config: ServiceConfig,
            storage_context: StorageContext,
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

        def sync_load() -> CriadexBaseIndex:
            return cls.from_vector_store(
                index_id=collection_name,
                embed_model=service_config.embed_model,
                vector_store=storage_context.vector_store,
                transformations=service_config.transformers,
                **kwargs
            )

        return await asyncio.to_thread(sync_load)

    @classmethod
    async def from_scratch(
            cls,
            collection_name: str,
            service_config: ServiceConfig,
            storage_context: StorageContext,
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

        def sync_load() -> CriadexBaseIndex:
            return cls.from_documents(
                documents=[cls.seed_document()],
                embed_model=service_config.embed_model,
                vector_store=storage_context.vector_store,
                transformations=service_config.transformers,
                storage_context=storage_context,
                **kwargs
            )

        instance: CriadexBaseIndex = await asyncio.to_thread(sync_load)
        instance.set_index_id(collection_name)
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

    def as_retriever(self, **kwargs: Any) -> QdrantVectorIndexRetriever:
        """
        Convert this index to a retriever using the custom Qdrant retriever built for Criadex

        :param kwargs: Initialization options
        :return: Criadex Qdrant retriever

        """

        return QdrantVectorIndexRetriever(
            self,
            node_ids=list(self.index_struct.nodes_dict.values()),
            **kwargs
        )
