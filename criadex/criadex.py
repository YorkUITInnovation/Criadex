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
import warnings
from asyncio import AbstractEventLoop, Task
from typing import Optional, Dict, List, Type

import aiomysql
from aiomysql import Pool
from grpc import StatusCode
from grpc.aio import AioRpcError
from llama_index.core.schema import Document
from qdrant_client import grpc, AsyncQdrantClient

from criadex.database.tables.documents import DocumentsModel
from criadex.database.tables.groups import GroupsModel
from criadex.database.tables.models.azure import AzureModelsModel, AzureModelsBaseModel
from criadex.database.tables.models.cohere import CohereModelsModel, CohereModelsBaseModel
from criadex.index.base_api import CriadexIndexAPI
from criadex.index.schemas import IndexTypeNotSupported, ServiceConfig, RawAsset, Bundle
from criadex.schemas import QdrantCredentials, MySQLCredentials
from .database.api import GroupDatabaseAPI
from .group import Group
from .index.index_api.document.index import DocumentIndexAPI
from .index.index_api.question.index import QuestionIndexAPI
from .index.llama_objects.models import CriaCohereRerank, CriaEmbedding
from .schemas import GroupConfig, GroupExistsError, GroupNotFoundError, IndexType, \
    DocumentExistsError, DocumentNotFoundError, ModelExistsError, ModelNotFoundError, \
    ModelInUseError


class Criadex:
    """
    This class initializes the Criadex object which can be used as a programmatic API.

    Criadex is an AI-powered search engine designed to apply a modern approach to semantic-based document search using vector databases.
    It can easily be integrated into any application to leverage intelligent document searching.


    """

    def __init__(
            self,
            qdrant_credentials: QdrantCredentials,
            mysql_credentials: MySQLCredentials
    ):
        """
        Initialize the Criadex object

        :param qdrant_credentials: Credentials for the Qdrant vector database
        :param mysql_credentials: Credentials for the MySQL database
        """

        # Credentials
        self._qdrant_credentials: QdrantCredentials = qdrant_credentials
        self._mysql_credentials: MySQLCredentials = mysql_credentials

        # Databases
        self._qdrant: Optional[AsyncQdrantClient] = None
        self._mysql_pool: Optional[Pool] = None
        self._mysql_api: Optional[GroupDatabaseAPI] = None

        # Other
        self._loop: Optional[AbstractEventLoop] = None
        self._active: Dict[str, Group] = dict()
        self._expire_task: Optional[Task] = None

    async def initialize(self) -> None:
        """
        Initialize Criadex databases & APIs. Should only be called once.

        :return: None

        """

        # Get the running loop on initialization
        self._loop = asyncio.get_running_loop()

        # Sync Vector DB Client
        self._qdrant: AsyncQdrantClient = AsyncQdrantClient(
            host=self._qdrant_credentials.host,
            port=self._qdrant_credentials.port,
            grpc_port=self._qdrant_credentials.grpc_port,
            prefer_grpc=True,
        )

        # SQL DB Startup
        self._mysql_pool: Pool = await self._create_mysql_pool()

        # SQL DB API Startup
        self._mysql_api: GroupDatabaseAPI = GroupDatabaseAPI(pool=self._mysql_pool)
        await self._mysql_api.initialize()

        # Expire Task Startup
        self._expire_task: Task = self._loop.create_task(self._expire_loop())

    async def _create_mysql_pool(self) -> Pool:
        """
        Create the MySQL pool. If the database does not exist, create it.
        :return: The pool instance

        """

        # First we initialize the DB
        async with aiomysql.connect(
                host=self._mysql_credentials.host,
                port=self._mysql_credentials.port,
                user=self._mysql_credentials.username,
                password=self._mysql_credentials.password,
                autocommit=True
        ) as connection:
            async with connection.cursor() as cursor:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=Warning)
                    await cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS "
                        f"{self._mysql_credentials.database}",
                    )

        # Then make a pool on the DB
        return await aiomysql.create_pool(
            host=self._mysql_credentials.host,
            port=self._mysql_credentials.port,
            user=self._mysql_credentials.username,
            password=self._mysql_credentials.password,
            autocommit=True,
            loop=self._loop,
            db=self._mysql_credentials.database
        )

    async def create(self, config: GroupConfig) -> None:
        """
        Create a Criadex index group

        :param config: Group configuration
        :return: None

        """

        if await self.exists(name=config.name):
            raise GroupExistsError()

        # MySQL Insert
        await self._mysql_api.groups.insert(
            name=config.name,
            type=IndexType[config.type].value,
            llm_model_id=config.llm_model_id,
            embedding_model_id=config.embedding_model_id,
            rerank_model_id=config.rerank_model_id
        )

        # Qdrant Insert
        try:
            index: CriadexIndexAPI = await self._build_index(group_name=config.name)
            await self._initialize_index(index=index)
        # Undo MySQL if Qdrant failed
        except Exception as ex:
            await self._mysql_api.groups.delete(name=config.name)
            raise ex

    async def delete(self, name: str) -> None:
        """
        Delete a Criadex index group

        :param name: The name of the index group
        :return: None

        """

        if not await self.exists(name=name):
            raise GroupNotFoundError()

        group_id: int = (await self.about(name=name)).id
        group: Group = await self.get(name=name)

        # Prevent later queries
        self._deactivate_group(name=name)

        # Delete Qdrant documents
        await group.delete()

        # Delete MySQL documents
        await self._mysql_api.assets.delete_all_group_assets(group_id=group_id)
        await self._mysql_api.documents.delete_all(group_id=group_id)

        # Delete group itself
        await self._mysql_api.groups.delete(name=name)

    async def get(self, name: str) -> Group:
        """
        Get an index group instance. If a group is not activate, this will activate it. If a group does not exist,
        this will throw a GroupNotFoundError

        :param name: The name of the index group
        :return: The instance

        """

        return self._active.get(name) or (await self.activate(name=name))

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

    async def exists(self, name: str) -> bool:
        """
        Check if an index group exists in the registry

        :param name: The name of the index group
        :return: Whether it exists

        """

        return await self._mysql_api.groups.exists(name=name)

    async def activate(self, name: str) -> Group:
        """
        Activate an EXISTING index

        :param name: Index name
        :return: Activated index

        """

        group: Optional[Group] = self._active.get(name)
        if group is not None:
            return group

        index: CriadexIndexAPI = await self._initialize_index(
            index=await self._build_index(group_name=name)
        )

        return Group(
            name=name,
            index=index
        )

    def is_active(self, name: str) -> bool:
        """
        Check if an index group is currently active

        :param name: Name of the index group
        :return: Whether it's active

        """

        return bool(self._active.get(name))

    async def insert_azure_model(self, config: AzureModelsBaseModel) -> AzureModelsModel:
        """
        Insert an azure model config into the MySQL registry

        :param config: The model config
        :return: The complete model config

        """

        model_id: Optional[int] = await self._mysql_api.azure_models.get_model_id(
            api_deployment=config.api_deployment,
            api_resource=config.api_resource
        )

        # Duplicate model
        if model_id is not None:
            raise ModelExistsError()

        return await self._mysql_api.azure_models.insert(config)

    async def update_azure_model(self, config: AzureModelsModel) -> AzureModelsModel:
        """
        Update an azure model config in the MySQL registry

        :param config: The complete model config
        :return: The complete model config

        """

        existent_model_id: int = await self._mysql_api.azure_models.get_model_id(
            api_deployment=config.api_deployment,
            api_resource=config.api_resource
        )

        # Model DNE
        if existent_model_id is None:
            raise ModelNotFoundError()

        # You are trying to create a model config that already exists (duplicates not allowed)
        # If this config already exists in a model we want to keep that integrity
        if existent_model_id != config.id:
            raise ModelExistsError()

        await self._mysql_api.azure_models.update(config)
        return await self._mysql_api.azure_models.retrieve(model_id=config.id)

    async def about_azure_model(self, model_id: int) -> AzureModelsModel:
        """
        Get information about an azure model config in the MySQL registry

        :param model_id: The ID of the model
        :return: The model instance

        """

        model: Optional[AzureModelsModel] = await self._mysql_api.azure_models.retrieve(model_id=model_id)

        if model is None:
            raise ModelNotFoundError()

        return model

    async def delete_azure_model(self, model_id: int) -> None:
        """
        Delete an azure model config in the MySQL registry

        :param model_id: The ID of the model
        :return: None

        """

        if not await self._mysql_api.azure_models.exists(model_id=model_id):
            raise ModelNotFoundError()

        if await self._mysql_api.azure_models.in_use(model_id=model_id):
            raise ModelInUseError()

        await self._mysql_api.azure_models.delete(model_id=model_id)

    async def exists_azure_model(self, model_id: int) -> bool:
        """
        Check if an azure model config in the MySQL registry exists

        :param model_id: ID of the model
        :return: Whether it exists

        """

        return await self._mysql_api.azure_models.exists(model_id=model_id)

    async def about_cohere_model(self, model_id: int) -> CohereModelsModel:
        """
        Get information about a cohere model config in the MySQL registry

        :param model_id: The ID of the model
        :return: The model instance

        """

        model: Optional[CohereModelsModel] = await self._mysql_api.cohere_models.retrieve(model_id=model_id)

        if model is None:
            raise ModelNotFoundError()

        return model

    async def delete_cohere_model(self, model_id: int) -> None:
        """
        Delete a Cohere model config in the MySQL registry

        :param model_id: The ID of the model
        :return: None

        """

        if not await self._mysql_api.cohere_models.exists(model_id=model_id):
            raise ModelNotFoundError()

        if await self._mysql_api.cohere_models.in_use(model_id=model_id):
            raise ModelInUseError()

        await self._mysql_api.cohere_models.delete(model_id=model_id)

    async def exists_cohere_model(self, model_id: int) -> bool:
        """
        Check if a Cohere model config in the MySQL registry exists

        :param model_id: ID of the model
        :return: Whether it exists

        """

        return await self._mysql_api.cohere_models.exists(model_id=model_id)

    async def insert_cohere_model(self, config: CohereModelsBaseModel) -> CohereModelsModel:
        """
        Insert an azure model config into the MySQL registry

        :param config: The model config
        :return: The complete model config

        """

        model_id: Optional[int] = await self._mysql_api.cohere_models.get_model_id(
            api_key=config.api_key,
            api_model=config.api_model
        )

        # Duplicate model
        if model_id is not None:
            raise ModelExistsError()

        return await self._mysql_api.cohere_models.insert(config)

    async def update_cohere_model(self, config: CohereModelsModel) -> None:
        """
        Update an azure model config in the MySQL registry

        :param config: The complete model config
        :return: The complete model config

        """

        # Model DNA
        if not await self._mysql_api.cohere_models.exists(model_id=config.id):
            raise ModelNotFoundError()

        # New combo already exists
        if await self._mysql_api.cohere_models.get_model_id(
                api_model=config.api_model, api_key=config.api_key
        ):
            raise ModelExistsError()

        # If this config already exists in a model we want to keep that integrity
        await self._mysql_api.cohere_models.update(config)

    async def get_model(
            self,
            group_name: str
    ) -> GroupsModel:
        """
        Get the model associated with an index group

        :param group_name: The name of the index group
        :return: The model

        """

        return await self._mysql_api.groups.retrieve(name=group_name)

    async def insert_file(self, group: Group, bundle: Bundle) -> int:
        """
        Insert a file bundle into the Vector DB and MySQL registry

        :param bundle: The bundle to insert
        :param group: The group to insert into
        :return: Token count of the file

        """

        assert group.name == bundle.group.name, "Group & bundle group mismatch"

        # Check if the document already exists
        if await self._mysql_api.documents.exists(group_id=bundle.group.id, document_name=bundle.name):
            raise DocumentExistsError()

        assets: List[RawAsset] = bundle.pop_assets()
        document: Document = bundle.to_document()

        # Insert nodes into Qdrant
        tokens: int = await group.index.insert(document=document)

        # Insert Document into MySQL
        document_id: int = await self._mysql_api.documents.insert(document_name=document.doc_id, group_id=bundle.group.id)

        # Add the assets (if there are any)
        for asset in assets:
            await self._mysql_api.assets.insert(
                group_id=bundle.group.id,
                document_id=document_id,
                asset=asset
            )

        # Calculate token count
        return tokens

    async def delete_file(self, group_name: str, document_name: str) -> None:
        """
        Delete a file from the Vector DB and MySQL registry

        :param group_name: The name of the index group
        :param document_name: The name of the document
        :return: None

        """

        group_id: int = await self.get_id(name=group_name)

        if not await self._mysql_api.documents.exists(group_id=group_id, document_name=document_name):
            raise DocumentNotFoundError()

        # Remove from Vector DB
        group: Group = await self.get(name=group_name)
        await group.remove(file_name=document_name)

        # Document reference
        document: DocumentsModel = await self._mysql_api.documents.retrieve(group_id=group_id, document_name=document_name)

        # Remove doc from MySQL DB
        await self._mysql_api.assets.delete_all_document_assets(document_id=document.id)
        await self._mysql_api.documents.delete(group_id=group_id, document_name=document_name)

    async def update_file(self, group: Group, bundle: Bundle) -> int:
        """
        Update the contents of a given file by effectively deleting and re-adding it.
        Will throw DocumentNotFoundError when trying to delete the file if it DNE.

        :param group: The group to update the file in
        :param bundle: The bundle to update
        :return: Number of tokens to index

        """

        # Delete it
        await self.delete_file(group_name=group.name, document_name=bundle.name)

        # Add it again
        return await self.insert_file(group=group, bundle=bundle)

    async def exists_file(self, group_name: str, document_name: str) -> bool:
        """
        Check if a given file exists in an index

        :param group_name: The name of the index group
        :param document_name: The document name to check against the index group
        :return: Whether it's there

        """

        # Get Row ID
        group_id: int = await self.get_id(name=group_name)

        # Whether it exists
        return await self._mysql_api.documents.exists(group_id=group_id, document_name=document_name)

    async def list_files(self, group_name: str) -> List[str]:
        """
        List all files in a given index

        :param group_name: The name of the index group
        :return: The list of document_names in it

        """

        # Get Row ID
        group_id: int = await self.get_id(name=group_name)

        results: List[DocumentsModel] = await self._mysql_api.documents.list(group_id=group_id)

        # Just extract the file names
        return [result.name for result in results]

    async def about(self, name: str) -> GroupsModel:
        """
        Get information about an index group

        :param name: The name of the index group
        :return: Its ORM MySQL model

        """

        group_model: Optional[GroupsModel] = await self._mysql_api.groups.retrieve(name=name)

        if group_model is None:
            raise GroupNotFoundError()

        return group_model

    @property
    def mysql_api(self) -> GroupDatabaseAPI:
        """
        Instance of the index group database API

        :return: IndexDatabaseAPI instance

        """

        return self._mysql_api

    async def _collection_exists(self, collection_name: str) -> bool:

        try:
            response: grpc.GetCollectionInfoResponse = await self._qdrant.grpc_collections.Get(
                grpc.GetCollectionInfoRequest(collection_name=collection_name)
            )
        except AioRpcError as ex:

            if ex.code() == StatusCode.NOT_FOUND:
                return False

            raise ex

        return response.result is not None

    async def _initialize_index(self, index: CriadexIndexAPI) -> CriadexIndexAPI:
        """
        Activate the LlamaIndex instance within an index

        :param index: the index group
        :return: Activated index

        """

        exists: bool = await self._collection_exists(index.collection_name())
        await index.initialize(is_new=not exists)

        return index

    def _deactivate_group(self, name: str, throw_error: bool = False) -> None:
        """
        Deactivate an index

        :param name: the index group to deactivate
        :param throw_error: Raise the error if it occurs
        :raises KeyError: When index DNA
        :return: None

        """

        try:
            del self._active[name]
        except KeyError as ex:
            if throw_error:
                raise ex

    @classmethod
    def _to_index_type(cls, index_type: IndexType) -> Optional[CriadexIndexAPI]:
        """
        Map a given MySQL type ID to its respective class

        :param index_type: The index type
        :return: The associated index

        """

        return (
            {
                index_type.DOCUMENT.value: DocumentIndexAPI,
                index_type.QUESTION.value: QuestionIndexAPI,
            }
        ).get(index_type.value, None)

    async def _build_index(self, group_name: str) -> CriadexIndexAPI:
        """
        Build a stored index from the MySQL DB

        :param group_name: The name of the index group
        :return: The instance

        """

        # Retrieve from DB
        index_model: GroupsModel = await self._mysql_api.groups.retrieve(name=group_name)

        if index_model is None:
            raise GroupNotFoundError()

        embedding_model: AzureModelsModel = await self._mysql_api.azure_models.retrieve(
            model_id=index_model.embedding_model_id
        )

        rerank_model: CohereModelsModel = await self._mysql_api.cohere_models.retrieve(
            model_id=index_model.rerank_model_id
        )

        index_type: Optional[Type[CriadexIndexAPI]] = self._to_index_type(IndexType(index_model.type))

        # Confirm retrieved
        if not all((embedding_model,)):
            raise GroupNotFoundError()

        # That would be awkward...
        if index_type is None:
            raise IndexTypeNotSupported("Index type not supported!")

        embedding: CriaEmbedding = index_type.build_embedding_model(
            azure_model=embedding_model
        )

        reranking: CriaCohereRerank = index_type.build_rerank_model(
            rerank_model=rerank_model
        )

        service_config: ServiceConfig = index_type.build_service_config(
            embed_model=embedding,
            rerank_model=reranking,
        )

        if index_type is DocumentIndexAPI:
            return DocumentIndexAPI(
                service_config=service_config,
                storage_context=DocumentIndexAPI.build_storage_context(self._qdrant),
                qdrant_client=self._qdrant,
                mysql_api=self._mysql_api
            )

        if index_type is QuestionIndexAPI:
            return QuestionIndexAPI(
                service_config=service_config,
                storage_context=QuestionIndexAPI.build_storage_context(self._qdrant),
                qdrant_client=self._qdrant,
                mysql_api=self._mysql_api
            )

        raise ValueError("Invalid index type!")

    async def _expire_loop(self) -> None:
        """
        Check if index groups are expired & deactivate them if they are

        :return: None

        """

        while True:

            for name, group in self._active.copy().items():

                # Check if expired
                if not group.expired:
                    continue

                self._deactivate_group(name=name)

            await asyncio.sleep(30)

    async def shutdown(self):
        """
        Shut down the Criadex instance
        :return: The instance

        """

        # Shut down MySQL connections gracefully
        await self._mysql_api.pool.clear()
        self._mysql_api.pool.close()
        await self._mysql_api.pool.wait_closed()

        # Close Qdrant client gracefully
        self._qdrant.close()
