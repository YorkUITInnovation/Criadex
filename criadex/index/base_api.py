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

from abc import abstractmethod
from typing import Optional, List, Sequence, Generic

import cohere
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle, Document, BaseNode
from llama_index.core.storage import StorageContext
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from criadex.database.tables.models.azure import AzureModelsModel
from criadex.database.tables.models.cohere import CohereModelsModel
from criadex.index.llama_objects.index_retriever import QdrantVectorIndexRetriever
from criadex.index.llama_objects.models import CriaEmbedding, CriaAzureOpenAI, CriaCohereRerank
from criadex.index.schemas import IndexResponse, \
    CriadexBaseIndex, SearchConfig, ServiceConfig, Bundle, BundleConfig
from .index_api.document.index_objects import FuzzyMetadataDuplicateRemovalPostProcessor, MetadataKeys
from .llama_objects.postprocessor import AsyncBaseNodePostprocessor
from .llama_objects.vector_store import CriadexQdrantVectorStore
from ..database.api import GroupDatabaseAPI
from ..database.tables.assets import AssetsModel
from ..database.tables.groups import GroupsModel


class ContentUploadConfig(BaseModel):
    """
    Configuration for uploading content to the index

    """

    file_name: str
    file_contents: dict
    file_metadata: dict


class CriadexIndexAPI(Generic[BundleConfig]):
    """
    API Wrapper for interacting with LlamaIndex-wrapped vector collections

    """

    TOP_N: int = None  # Let the CLIENT decide what is relevant. Pull & rank ALL
    MAX_TOP_K: int = 1000  # Limit the user to a max top K for resource usage purposes

    def __init__(
            self,
            service_config: ServiceConfig,
            storage_context: StorageContext,
            qdrant_client: AsyncQdrantClient,
            mysql_api: GroupDatabaseAPI
    ):
        self._service_config: ServiceConfig = service_config
        self._storage_context: StorageContext = storage_context
        self._qdrant_client: AsyncQdrantClient = qdrant_client
        self._index: Optional[CriadexBaseIndex] = None
        self._mysql_api: GroupDatabaseAPI = mysql_api
        self._fuzzy: FuzzyMetadataDuplicateRemovalPostProcessor = FuzzyMetadataDuplicateRemovalPostProcessor(
            target_metadata_key=MetadataKeys.WINDOW
        )

    async def search(
            self,
            config: SearchConfig
    ) -> IndexResponse:
        """
        Search the index group & receive relevant data

        :param config: Configuration for searching
        :return: The response

        """

        # Validate the prompt first
        CriaAzureOpenAI.validate_prompt(prompt=config.prompt)
        search_response: List[NodeWithScore] = await self._search(config)
        search_response_assets: List[AssetsModel] = []
        search_response_serialized: List[dict] = []

        for node in search_response:
            search_response_serialized.append(
                node.model_dump()
            )

            if 'asset_uuid' not in node.node.metadata:
                continue

            asset: AssetsModel = await self._mysql_api.assets.retrieve(
                group_id=node.node.metadata['group_id'],
                asset_uuid=node.node.metadata['asset_uuid']
            )

            if asset is not None:
                search_response_assets.append(asset)

        return IndexResponse(
            nodes=search_response_serialized,
            assets=search_response_assets,
            search_units=1 if config.rerank_enabled else 0
        )

    async def _search(self, config: SearchConfig) -> List[NodeWithScore]:
        """
        Search the index & receive relevant data as a string

        :param config: Configuration for searching the index
        :return: List of nodes, with their associated, re-ranked scores

        """

        query_bundle: QueryBundle = QueryBundle(config.prompt)
        retriever: QdrantVectorIndexRetriever = self._index.as_retriever(
            similarity_top_k=min(config.top_k, self.MAX_TOP_K)
        )

        # Top K
        nodes: List[NodeWithScore] = await retriever.afilter_retrieve(
            query_bundle=query_bundle,
            query_filter=config.search_filter
        )

        # Min K
        nodes = [node for node in nodes if node.score >= config.min_k]

        # Apply postprocessors (incl. re-ranking)
        nodes = await self.postprocess_nodes(query_bundle, nodes, self.node_postprocessors(config))

        # Is Rerank Enabled
        if config.rerank_enabled:
            # Top N
            nodes = nodes[:config.top_n]

            # Min N
            nodes = [node for node in nodes if node.score >= config.min_n]

        # Then remove fuzzy dupes
        return self._fuzzy.postprocess_nodes(nodes, query_bundle)

    @classmethod
    async def postprocess_nodes(
            cls,
            query_bundle: QueryBundle,
            nodes: List[NodeWithScore],
            node_postprocessors: List[BaseNodePostprocessor]
    ) -> List[NodeWithScore]:
        """
        Apply various postprocessors to the nodes

        :param query_bundle: The query bundle
        :param nodes: The nodes to postprocess
        :param node_postprocessors: The postprocessors to apply
        :return: List of postprocessed nodes

        """

        # Apply postprocessors (incl. reranking)
        for post_processor in node_postprocessors:

            if isinstance(post_processor, AsyncBaseNodePostprocessor):
                nodes = await post_processor.postprocess_nodes(
                    nodes=nodes,
                    query_bundle=query_bundle
                )
            else:
                nodes = post_processor.postprocess_nodes(
                    nodes=nodes,
                    query_bundle=query_bundle
                )

        return nodes

    async def insert(
            self,
            document: Document
    ) -> int:
        """
        Insert a file into the index group

        :param document: The document nodes to insert
        :param document: The document to insert
        :return: The token cost to insert the file

        """

        return await self._index.insert_document(
            document=document
        )

    @property
    def qdrant_client(self) -> AsyncQdrantClient:
        """
        Getter for the Qdrant client

        :return: The Qdrant client

        """

        return self._qdrant_client

    @abstractmethod
    async def convert(self, group_model: GroupsModel, file: ContentUploadConfig) -> Bundle[BundleConfig]:
        """
        Convert an UNPROCESSED file into a compatible bundle

        :param group_model: The group the file will belong to
        :param file: The unprocessed file
        :return: The new, processed file

        """

        raise NotImplementedError

    @abstractmethod
    async def initialize(self, is_new: bool) -> None:
        """
        Initialize the index

        :param is_new: If the index is new, this signals we should create it
        :return: None

        """

        raise NotImplementedError

    @property
    def service_config(self) -> ServiceConfig:
        """
        Get the service configuration for the current index

        :return: The service config

        """

        return self._service_config

    @property
    def storage_context(self) -> StorageContext:
        """
        Get the storage context for the current index

        :return: The storage context

        """
        return self._storage_context

    @classmethod
    @abstractmethod
    def build_service_config(
            cls,
            embed_model: CriaEmbedding,
            rerank_model: CriaCohereRerank,
    ) -> ServiceConfig:
        """
        Build the service configuration for the index

        :param embed_model: The embedding model
        :param rerank_model: The re-rank model
        :return: The service configuration

        """

        raise NotImplementedError

    @classmethod
    def build_storage_context(cls, client: AsyncQdrantClient) -> StorageContext:
        """
        Build the storage context for this index

        :param client: Async Qdrant client
        :return: The storage context using qdrant

        """

        return StorageContext.from_defaults(
            vector_store=CriadexQdrantVectorStore(
                aclient=client,
                collection_name=cls.collection_name()
            )
        )

    @abstractmethod
    def node_postprocessors(self, config: SearchConfig) -> List[BaseNodePostprocessor]:
        """
        Get the postprocessors for the index

        :param config: The search configuration
        :return: The postprocessors

        """

        raise NotImplementedError

    @classmethod
    @abstractmethod
    def collection_name(cls) -> str:
        """
        Get the collection name for the index

        :return: The collection name

        """

        raise NotImplementedError

    @classmethod
    def build_embedding_model(cls, azure_model: AzureModelsModel, **kwargs) -> CriaEmbedding:
        """
        Build the embedding model for this index

        :param azure_model: The Azure model
        :param kwargs: Keyword args (llama-index) to initialize with
        :return: The embedding model

        """

        return CriaEmbedding(
            model=azure_model.api_model,
            api_key=azure_model.api_key,
            api_version=azure_model.api_version,
            azure_endpoint=azure_model.api_base,
            azure_deployment=azure_model.api_deployment,
            **kwargs
        )

    @classmethod
    def build_rerank_model(cls, rerank_model: CohereModelsModel, **_) -> CriaCohereRerank:
        """
        Build the re-rank model for this index

        :param rerank_model: The re-rank model
        :param _: No kwargs accepted
        :return: The re-rank model

        """

        return CriaCohereRerank(
            client=cohere.AsyncClient(api_key=rerank_model.api_key),
            model=rerank_model.api_model
        )

    @classmethod
    def build_llm_model(cls, azure_model: AzureModelsModel, **kwargs) -> CriaAzureOpenAI:
        """
        Build the LLM model for this index

        :param azure_model: The Azure model
        :param kwargs: The keyword args to initialize with
        :return: The LLM model

        """

        if "max_tokens" in kwargs:
            kwargs["max_tokens"] = max(1, kwargs["max_tokens"])

        return CriaAzureOpenAI(
            model=azure_model.api_model,
            api_key=azure_model.api_key,
            api_version=azure_model.api_version,
            azure_endpoint=azure_model.api_base,
            engine=azure_model.api_deployment,
            **kwargs
        )
