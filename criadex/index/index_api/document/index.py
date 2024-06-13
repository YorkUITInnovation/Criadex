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

from typing import List

from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.storage import StorageContext

from criadex.index.base_api import CriadexIndexAPI, ContentUploadConfig
from criadex.index.index_api.document.index_objects import DocumentCohereRerank, DocumentConfig, MetadataKeys, \
    DocumentParser
from criadex.index.index_api.document.store_index import DocumentVectorStoreIndex
from criadex.index.llama_objects.extra_utils import NodeTokenParser
from criadex.index.llama_objects.models import CriaEmbedding, CriaCohereRerank
from criadex.index.llama_objects.schemas import CriadexFile
from criadex.index.llama_objects.vector_store import CriadexQdrantVectorStore
from criadex.index.schemas import QdrantConfig, SearchConfig, ServiceConfig


class DocumentIndexAPI(CriadexIndexAPI):
    """
    Document index. This index type allows for the storage and retrieval of document nodes.

    """

    async def initialize(self, is_new: bool) -> None:
        """
        Initialize the index

        :param is_new: Run the creation variant if True
        :return: None

        """

        self._index = await (
            DocumentVectorStoreIndex.from_scratch if is_new else DocumentVectorStoreIndex.from_store
        )(
            collection_name=self.collection_name(),
            service_config=self._service_config,
            storage_context=self._storage_context
        )

    @classmethod
    def build_storage_context(cls, store_config: QdrantConfig) -> StorageContext:
        """
        Build the storage context for this index

        :param store_config: Qdrant config for storage
        :return: The storage context using qdrant

        """

        return StorageContext.from_defaults(
            vector_store=CriadexQdrantVectorStore(
                client=store_config.qdrant_client,
                aclient=store_config.qdrant_aclient,
                collection_name=cls.collection_name()
            )
        )

    @classmethod
    def build_service_config(
            cls,
            embed_model: CriaEmbedding,
            rerank_model: CriaCohereRerank,
    ) -> ServiceConfig:
        """
        Build the service config for this index

        :param embed_model: The embedding model
        :param rerank_model: The rerank model
        :return: The service config instance

        """

        return ServiceConfig(
            embed_model=embed_model,
            rerank_model=rerank_model,
            transformers=[DocumentParser(embed_model=embed_model), NodeTokenParser(embedding_model=embed_model)]
        )

    def node_postprocessors(self, config: SearchConfig) -> List[BaseNodePostprocessor]:
        """
        Get the node postprocessors to be used given the search config

        :param config: The search config
        :return: The node postprocessors

        """

        if not isinstance(self._service_config.rerank_model, CriaCohereRerank):
            raise ValueError("This index requires a CriaCohereRerank model!")

        postprocessors = [
            MetadataReplacementPostProcessor(
                target_metadata_key=MetadataKeys.WINDOW
            )
        ]

        if config.rerank_enabled:
            postprocessors.append(
                DocumentCohereRerank(
                    reranker=self._service_config.rerank_model,
                    top_n=self.TOP_N
                )
            )

        return postprocessors

    async def _convert(self, group_name: str, file: ContentUploadConfig) -> CriadexFile:
        """
        Convert a generic file to a CriadexFile

        :param group_name: The group name
        :param file: The file to convert
        :return: Converted file

        """

        config: DocumentConfig = DocumentConfig(**file.file_contents)

        return CriadexFile.create(
            file_name=file.file_name,
            text=config.json(),
            file_group=group_name,
            file_metadata=file.file_metadata
        )

    @classmethod
    def collection_name(cls) -> str:
        """
        Get the name of the collection

        :return: The collection name

        """

        return "document-index"
