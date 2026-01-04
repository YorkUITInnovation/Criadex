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
import logging
import time
from typing import Optional
import aiomysql
from criadex.bot.bot import Bot
from criadex.cache.cache import Cache
from criadex.database.api import GroupDatabaseAPI
from criadex.schemas import MySQLCredentials, ElasticsearchCredentials, GroupConfig, GroupExistsError, IndexType, GroupNotFoundError, DocumentExistsError, DocumentNotFoundError
from criadex.database.tables.groups import GroupsModel
from criadex.database.tables.documents import DocumentsModel
from app.core.schemas import AppMode
from app.core import config
from criadex.database.tables.models.cohere import COHERE_MODELS, CohereModelsBaseModel, CohereModelsModel
from criadex.database.tables.models.azure import AZURE_MODELS, AzureModelsBaseModel, AzureModelsModel
from criadex.index.schemas import SearchConfig
from criadex.schemas import ModelExistsError
from criadex.core.event import Event
from criadex.index.ragflow_objects.vector_store import RagflowVectorStore
from criadex.index.ragflow_objects.embedder import RagflowEmbedder
from criadex.index.ragflow_objects.retriever import RagflowRetriever

from criadex.index.index_api.document.index_objects import DocumentConfig

class Criadex:
    """
    Criadex is a semantic search engine developed by UIT Innovation at York University with a targetted focus on
    generative AI for higher education.

    """

    def __init__(
        self,
        mysql_credentials: MySQLCredentials,
        elasticsearch_credentials: ElasticsearchCredentials,
    ):
        # Credentials
        self.mysql_credentials = mysql_credentials
        self.elasticsearch_credentials = elasticsearch_credentials

        # APIs and features
        self.mysql_api = None
        self.vector_store = None
        self.bot = None
        self.cache = None
        self.event = Event()
        self._active = {}

    async def initialize(self) -> None:
        """
        Initialize Criadex
        """
        # MySQL
        self.mysql_pool = await aiomysql.create_pool(
            host=self.mysql_credentials.host,
            port=self.mysql_credentials.port,
            user=self.mysql_credentials.username,
            password=self.mysql_credentials.password,
            db=self.mysql_credentials.database,
            autocommit=True
        )
        self.mysql_api = GroupDatabaseAPI(self.mysql_pool)
        await self.mysql_api.initialize()

        # Populate default models if empty and not in testing mode
        if config.APP_MODE != AppMode.TESTING:
            await self.mysql_api.cohere_models.truncate()
            for model_name in COHERE_MODELS.__args__:
                await self.mysql_api.cohere_models.insert(
                    CohereModelsBaseModel(
                        api_model=model_name,
                        api_key=""
                    )
                )
            await self.mysql_api.azure_models.truncate()
            for model_name in AZURE_MODELS.__args__:
                await self.mysql_api.azure_models.insert(
                    AzureModelsBaseModel(
                        api_model=model_name,
                        api_resource=f"your-resource-{model_name}",
                        api_deployment=f"your-deployment-{model_name}"
                    )
                )


        # Ragflow/Elasticsearch integration
        self.vector_store = RagflowVectorStore(
            host=self.elasticsearch_credentials.host,
            port=self.elasticsearch_credentials.port,
            username=self.elasticsearch_credentials.username,
            password=self.elasticsearch_credentials.password,
            index_name="criadex"
        )
        self.embedder = RagflowEmbedder()
        self.retriever = RagflowRetriever(self.vector_store, self.embedder)

        # Criadex features
        self.bot = Bot(self.vector_store, self.embedder, event=self.event)
        self.cache = Cache(self.mysql_api, event=self.event)
        # Example: emit event hooks for search/insert/delete
        # self.event.on(Event.SEARCH, lambda query: logging.info(f"Search event: {query}"))
        # self.event.on(Event.INSERT, lambda doc: logging.info(f"Insert event: {doc}"))
        # self.event.on(Event.DELETE, lambda doc_id: logging.info(f"Delete event: {doc_id}"))

    async def exists(self, name: str) -> bool:
        """
        Check if an index group exists in the registry

        :param name: The name of the index group
        :return: Whether it exists

        """

        return await self.mysql_api.groups.exists(name=name)

    async def create(self, config: GroupConfig) -> None:
        """
        Create a Criadex index group

        :param config: Group configuration
        :return: None

        """

        if await self.exists(name=config.name):
            raise GroupExistsError()

        # MySQL Insert
        await self.mysql_api.groups.insert(
            name=config.name,
            type=IndexType[config.type].value,
            llm_model_id=config.llm_model_id,
            embedding_model_id=config.embedding_model_id,
            rerank_model_id=config.rerank_model_id
        )

        # Vector store index creation is often implicit on first insert.
        # This block is for safety and future explicit index creation logic.
        try:
            await self.vector_store.acreate_collection(collection_name=config.name)
        except Exception as ex:
            # If vector store operations fail, roll back the MySQL insertion.
            await self.mysql_api.groups.delete(name=config.name)
            raise ex

    async def about(self, name: str) -> GroupsModel:
        """
        Get information about an index group

        :param name: The name of the index group
        :return: Its ORM MySQL model

        """

        group_model: Optional[GroupsModel] = await self.mysql_api.groups.retrieve(name=name)

        if group_model is None:
            raise GroupNotFoundError()

        return group_model

    async def delete(self, name: str) -> None:
        """
        Delete a Criadex index group

        :param name: The name of the index group
        :return: None

        """

        if not await self.exists(name=name):
            raise GroupNotFoundError()

        group_id: int = (await self.about(name=name)).id

        # Delete MySQL documents and assets
        await self.mysql_api.assets.delete_all_group_assets(group_id=group_id)
        await self.mysql_api.documents.delete_all(group_id=group_id)

        # Delete group itself
        await self.mysql_api.groups.delete(name=name)

    async def get_id(
            self,
            name: str,
            throw_not_found: bool = True
    ) -> int:
        """
        Get an index group's ID from the MySQL database

        :param throw_not_found: Whether to throw error when ID not found
        :param name: The name of the index group
        :return: The ID

        """

        try:
            return (await self.about(name=name)).id
        except GroupNotFoundError as ex:
            if throw_not_found:
                raise ex

    async def get(self, name: str) -> 'Criadex':
        """
        Get an index group instance.

        :param name: The name of the index group
        :return: The Criadex instance

        """
        if not await self.exists(name=name):
            raise GroupNotFoundError()
        return self

    async def insert_file(self, group_name: str, file_name: str, file_contents: dict, file_metadata: dict) -> int:
        """
        Insert a file into the group.
        """
        group_id = await self.get_id(name=group_name)

        if await self.mysql_api.documents.exists(group_id=group_id, document_name=file_name):
            raise DocumentExistsError()

        total_tokens = 0
        nodes_to_insert = []

        if 'nodes' in file_contents:
            doc_config = DocumentConfig(**file_contents)
            for node in doc_config.nodes:
                # Preserve the original metadata from the node
                node_data = {
                    'text': node.text, 
                    'metadata': node.metadata.copy() if node.metadata else {}
                }
                nodes_to_insert.append(node_data)
        elif 'questions' in file_contents:
            # For QuestionConfig, create a node for each question and the answer
            for question_text in file_contents['questions']:
                nodes_to_insert.append({'text': question_text, 'metadata': {}, 'type': 'NarrativeText'})
            if 'answer' in file_contents:
                nodes_to_insert.append({'text': file_contents['answer'], 'metadata': {}, 'type': 'NarrativeText'})

        for i, node_data in enumerate(nodes_to_insert):
            text = node_data['text']
            
            # Start with the node's existing metadata, then add system metadata and file_metadata
            metadata = node_data.get('metadata', {}).copy()
            metadata.update(file_metadata) # <--- Add this line to merge file_metadata
            metadata.update({
                'file_name': file_name,
                'updated_at': int(time.time() * 1000)
            })
            
            embedding = self.embedder.embed(text)
            total_tokens += len(text.split())
            doc_id = f"{file_name}-{i}"

            await self.vector_store.ainsert(
                collection_name=group_name,
                doc_id=doc_id,
                embedding=embedding,
                text=text,
                metadata=metadata
            )

        await self.mysql_api.documents.insert(document_name=file_name, group_id=group_id)

        return total_tokens

    async def delete_file(self, group_name: str, document_name: str) -> None:
        group_id: int = await self.get_id(name=group_name)
        if not await self.mysql_api.documents.exists(group_id=group_id, document_name=document_name):
            raise DocumentNotFoundError()
        document: DocumentsModel = await self.mysql_api.documents.retrieve(group_id=group_id, document_name=document_name)

        await self.vector_store.adelete_by_query(
            collection_name=group_name,
            field="file_name",
            value=document_name
        )

        await self.mysql_api.assets.delete_all_document_assets(document_id=document.id)
        await self.mysql_api.documents.delete(group_id=group_id, document_name=document.name)

    async def update_file(self, group_name: str, file_name: str, file_contents: dict, file_metadata: dict) -> int:
        await self.delete_file(group_name=group_name, document_name=file_name)
        result = await self.insert_file(group_name=group_name, file_name=file_name, file_contents=file_contents, file_metadata=file_metadata)
        # Clear cache for this group/file after update
        if self.cache:
            self.cache.clear()
        return result

    async def list_files(self, group_name: str) -> list[str]:
        """
        List all files in a given index

        :param group_name: The name of the index group
        :return: The list of document_names in it

        """

        # Get Row ID
        group_id: int = await self.get_id(name=group_name)

        results: list[DocumentsModel] = await self.mysql_api.documents.list(group_id=group_id)

        # Just extract the file names
        return [result.name for result in results]


    async def shutdown(self) -> None:
        """
        Shutdown Criadex

        :return: None

        """

        await self.mysql_api.shutdown()
        self.mysql_pool.close()
        await self.mysql_pool.wait_closed()
        # Give the async loop a moment to close the connection
        await asyncio.sleep(0.25)

    # Example methods to show event usage (replace with your actual logic)
    async def search(self, group_name: str, query: SearchConfig, top_k=10, query_filter: Optional[dict] = None):
        if not await self.exists(name=group_name):
            raise GroupNotFoundError()

        # Use bot for semantic search and cache results
        self.event.emit(Event.SEARCH, query=query)
        
        # Create a hashable key from the Pydantic model
        cache_key = query.model_dump_json()
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached # Return the cached result
        
        # If not cached, perform the search
        results = await self.bot.search(group_name, query.query, top_k=query.top_k, query_filter=query_filter)
        
        # Cache the new result
        self.cache.set(cache_key, results)
        
        return results

    async def insert_azure_model(self, config: AzureModelsBaseModel) -> AzureModelsModel:
        """
        Insert an Azure model config into the database.
        
        :param config: The Azure model configuration
        :return: The created AzureModelsModel with ID
        :raises ModelExistsError: If a model with the same api_resource and api_deployment already exists
        """
        # Check for duplicate based on composite unique constraint (api_resource, api_deployment)
        existing_id = await self.mysql_api.azure_models.get_model_id(
            api_deployment=config.api_deployment,
            api_resource=config.api_resource
        )
        if existing_id is not None:
            raise ModelExistsError(
                f"That deployment '{config.api_deployment}' already exists in the database for Azure resource '{config.api_resource}'!"
            )
        
        return await self.mysql_api.azure_models.insert(config=config)

    async def insert_cohere_model(self, config: CohereModelsBaseModel) -> CohereModelsModel:
        """
        Insert a Cohere model config into the database.
        
        :param config: The Cohere model configuration
        :return: The created CohereModelsModel with ID
        :raises ModelExistsError: If a model with the same api_key and api_model already exists
        """
        # Check for duplicate - need to check if model exists for this API key
        # This depends on the CohereModels table structure, but typically it's (api_key, api_model) unique
        # For now, we'll catch the database error if it exists, or check if we have a similar get_model_id method
        try:
            return await self.mysql_api.cohere_models.insert(config=config)
        except Exception as e:
            # If it's a duplicate key error, raise ModelExistsError
            if "Duplicate" in str(e) or "1062" in str(e):
                raise ModelExistsError(
                    f"That model already exists for that Cohere API key!"
                )
            raise

    async def exists_azure_model(self, model_id: int) -> bool:
        """
        Check if an Azure model exists by ID.
        
        :param model_id: The model ID
        :return: Whether the model exists
        """
        return await self.mysql_api.azure_models.exists(model_id=model_id)

    async def about_azure_model(self, model_id: int) -> AzureModelsModel:
        """
        Retrieve an Azure model by ID or raise if not found.
        """
        model = await self.mysql_api.azure_models.retrieve(model_id=model_id)
        if model is None:
            from criadex.schemas import ModelNotFoundError
            raise ModelNotFoundError()
        return model

    async def delete_azure_model(self, model_id: int) -> None:
        """
        Delete an Azure model by ID. Raise ModelNotFoundError if missing and
        ModelInUseError if referenced by any group.
        """
        from criadex.schemas import ModelNotFoundError, ModelInUseError
        if not await self.mysql_api.azure_models.exists(model_id=model_id):
            raise ModelNotFoundError()
        if await self.mysql_api.azure_models.in_use(model_id=model_id):
            raise ModelInUseError()
        await self.mysql_api.azure_models.delete(model_id=model_id)

    async def update_azure_model(self, config: AzureModelsModel) -> AzureModelsModel:
        """
        Update an existing Azure model; ensure composite (api_resource, api_deployment) remains unique.
        """
        # If api_resource/api_deployment changed to an existing pair, block
        existing_id = await self.mysql_api.azure_models.get_model_id(
            api_deployment=config.api_deployment,
            api_resource=config.api_resource
        )
        if existing_id is not None and existing_id != config.id:
            raise ModelExistsError(
                f"That deployment '{config.api_deployment}' already exists in the database for Azure resource '{config.api_resource}'!"
            )
        return await self.mysql_api.azure_models.update(config=config)

    async def about_cohere_model(self, model_id: int) -> CohereModelsModel:
        """
        Retrieve a Cohere model by ID or raise if not found.
        """
        model = await self.mysql_api.cohere_models.retrieve(model_id=model_id)
        if model is None:
            from criadex.schemas import ModelNotFoundError
            raise ModelNotFoundError()
        return model

    async def update_cohere_model(self, config: CohereModelsModel) -> CohereModelsModel:
        """
        Update an existing Cohere model; ensure (api_key, api_model) remains unique if relevant.
        """
        # If api_key/api_model pair conflicts with another, block
        existing_id = await self.mysql_api.cohere_models.get_model_id(
            api_key=config.api_key,
            api_model=config.api_model
        )
        if existing_id is not None and existing_id != config.id:
            raise ModelExistsError(
                "That model already exists for that Cohere API key!"
            )
        await self.mysql_api.cohere_models.update(config=config)
        # Return the fresh model
        return await self.about_cohere_model(model_id=config.id)

    async def delete_cohere_model(self, model_id: int) -> None:
        """
        Delete a Cohere model by ID. Raise ModelNotFoundError if missing and
        ModelInUseError if referenced by any group.
        """
        from criadex.schemas import ModelNotFoundError, ModelInUseError
        if not await self.mysql_api.cohere_models.exists(model_id=model_id):
            raise ModelNotFoundError()
        if await self.mysql_api.cohere_models.in_use(model_id=model_id):
            raise ModelInUseError()
        await self.mysql_api.cohere_models.delete(model_id=model_id)