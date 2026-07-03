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
import gc
import json
import logging
import os
import time
import uuid
from typing import Iterable, Iterator, Optional, Tuple
import aiomysql
from elasticsearch import NotFoundError as ESNotFoundError
from criadex.bot.bot import Bot
from criadex.cache.cache import Cache
from criadex.cache.api import CriadexCacheAPI
from criadex.database.api import GroupDatabaseAPI
from criadex.schemas import MySQLCredentials, ElasticsearchCredentials, GroupConfig, GroupExistsError, IndexType, GroupNotFoundError, DocumentExistsError, DocumentNotFoundError, IndexNotFoundError
from criadex.database.tables.groups import GroupsModel
from criadex.database.tables.documents import DocumentsModel
from app.core.schemas import AppMode
from app.core import config
from criadex.database.tables.models.cohere import COHERE_MODELS, CohereModelsBaseModel, CohereModelsModel
from criadex.database.tables.models.azure import AZURE_MODELS, AzureModelsBaseModel, AzureModelsModel
from criadex.database.tables.models.generic import GenericModelsModel
from criadex.index.schemas import SearchConfig
from criadex.schemas import ModelExistsError
from criadex.core.event import Event
from criadex.index.ragflow_objects.vector_store import RagflowVectorStore
from criadex.index.ragflow_objects.embedder import RagflowEmbedder
from criadex.index.ragflow_objects.retriever import RagflowRetriever
from criadex.index.ragflow_objects.graph_rag import RagflowGraphRAGClient
from criadex.index.ragflow_objects.kb_sync import RagflowKbSync

from criadex.index.index_api.document.index_objects import DocumentConfig
from criadex.graph import GroupGraphStore

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
        self._redis_pool = None
        self._redis_api: Optional[CriadexCacheAPI] = None
        self.event = Event()
        self._active = {}
        self.graph_store = GroupGraphStore()
        self.graph_rag_client = RagflowGraphRAGClient()
        self.kb_sync: Optional[RagflowKbSync] = None
        self._graph_job_tasks: dict[str, asyncio.Task] = {}
        self._ingest_batch_size = max(1, int(os.getenv("CRIADEX_INGEST_BATCH_SIZE", "32")))
        self._ingest_gc_every_batches = max(0, int(os.getenv("CRIADEX_INGEST_GC_EVERY_BATCHES", "4")))

    @staticmethod
    def _iter_file_entries(file_contents: dict) -> Iterator[Tuple[str, dict]]:
        if 'nodes' in file_contents:
            for node_data in file_contents.get('nodes') or []:
                if isinstance(node_data, dict):
                    text = str(node_data.get('text', ''))
                    metadata = dict(node_data.get('metadata') or {})
                else:
                    text = str(getattr(node_data, 'text', ''))
                    metadata = dict(getattr(node_data, 'metadata', {}) or {})
                yield text, metadata
            return

        if 'questions' in file_contents:
            for question in file_contents.get('questions') or []:
                yield str(question), {}
            if 'answer' in file_contents:
                yield str(file_contents['answer']), {}

    @staticmethod
    def _batch_iterable(items: Iterable[Tuple[int, Tuple[str, dict]]], batch_size: int) -> Iterator[list[Tuple[int, Tuple[str, dict]]]]:
        batch: list[Tuple[int, Tuple[str, dict]]] = []
        for item in items:
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _schedule_kb_sync(self, coro) -> None:
        """Run Ragflow KB sync in the background so API requests are not blocked."""

        async def _runner():
            try:
                await coro
            except Exception as exc:
                logging.warning("Ragflow KB sync background task failed: %s", exc)

        asyncio.create_task(_runner())

    async def _ensure_database_exists(self) -> None:
        """
        Create the configured MySQL database if it doesn't exist yet.

        aiomysql.create_pool(db=...) fails hard with "Unknown database" if the
        database hasn't been created — connect without a database first to
        create it, matching Criabot's bootstrap pattern.
        """
        bootstrap_conn = await aiomysql.connect(
            host=self.mysql_credentials.host,
            port=self.mysql_credentials.port,
            user=self.mysql_credentials.username,
            password=self.mysql_credentials.password,
            autocommit=True,
        )
        try:
            async with bootstrap_conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.mysql_credentials.database}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            bootstrap_conn.close()

    async def initialize(self) -> None:
        """
        Initialize Criadex
        """
        # MySQL
        await self._ensure_database_exists()
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

        from criadex.migrations.runner import MigrationRunner
        await MigrationRunner(self.mysql_pool).run_pending()

        # kb_sync is wired with vector_store/embedder after those are initialised below.

        # Seed catalog templates only when tables are empty (non-testing).
        if config.APP_MODE != AppMode.TESTING:
            existing_cohere = await self.mysql_api.cohere_models.get_all()
            if not existing_cohere:
                for model_name in COHERE_MODELS.__args__:
                    await self.mysql_api.cohere_models.insert(
                        CohereModelsBaseModel(
                            api_model=model_name,
                            api_key=""
                        )
                    )
            existing_azure = await self.mysql_api.azure_models.get_all()
            if not existing_azure:
                for model_name in AZURE_MODELS.__args__:
                    await self.mysql_api.azure_models.insert(
                        AzureModelsBaseModel(
                            api_model=model_name,
                            api_resource=f"your-resource-{model_name}",
                            api_deployment=f"your-deployment-{model_name}"
                        )
                    )

            try:
                from criadex.index.ragflow_objects.model_sync import sync_ragflow_models
                await sync_ragflow_models(self.mysql_api)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Ragflow model sync during initialize skipped: %s",
                    exc,
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
        try:
            self.embedding_dims = len(self.embedder.embed("dimension probe"))
        except Exception:
            self.embedding_dims = 768
        self.vector_store.embedding_dims = self.embedding_dims
        self.retriever = RagflowRetriever(self.vector_store, self.embedder)

        self.kb_sync = RagflowKbSync(
            self.mysql_pool,
            self.mysql_api,
            vector_store=self.vector_store,
            embedder=self.embedder,
        )

        # Criadex features
        self.bot = Bot(self.vector_store, self.embedder, event=self.event)
        self.cache = Cache(self.mysql_api, event=self.event)

        # Redis cache (optional — falls back to in-process LRU when unconfigured)
        if config.REDIS_CREDENTIALS is not None:
            try:
                from redis import asyncio as aioredis
                rc = config.REDIS_CREDENTIALS
                self._redis_pool = aioredis.ConnectionPool(
                    host=rc.host,
                    port=rc.port,
                    password=rc.password,
                    db=rc.db,
                    max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
                    socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "3")),
                    socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS", "3")),
                    health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL_SECONDS", "30")),
                )
                self._redis_api = CriadexCacheAPI(pool=self._redis_pool)
                logging.info("Criadex Redis cache connected (host=%s db=%s)", rc.host, rc.db)
            except Exception as exc:
                logging.warning("Criadex Redis cache unavailable, falling back to in-process cache: %s", exc)
                self._redis_pool = None
                self._redis_api = None

        await self._recover_graph_jobs()
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
        try:
            await self.mysql_api.groups.insert(
                name=config.name,
                type=IndexType[config.type].value,
                llm_model_id=config.llm_model_id,
                embedding_model_id=config.embedding_model_id,
                rerank_model_id=config.rerank_model_id
            )
        except Exception as ex:
            message = str(ex).lower()
            if "duplicate entry" in message or "1062" in message:
                raise GroupExistsError() from ex
            raise

        # Vector store index creation is critical - the embedding field MUST be dense_vector type
        # If this fails, documents cannot be indexed/searched properly
        try:
            # Reused group names must start from a clean vector collection.
            # Older deployments may have left stale indices behind after delete.
            await self.vector_store.adelete_collection(collection_name=config.name)
        except Exception as ex:
            logging.warning(
                "Criadex: could not pre-clean Elasticsearch index for group '%s': %s",
                config.name,
                ex,
            )

        try:
            await self.vector_store.acreate_collection(
                collection_name=config.name,
                embedding_dims=self.embedding_dims,
            )
        except Exception as ex:
            # Index creation is critical - propagate the error so the group creation fails
            logging.error(
                "Criadex: CRITICAL - Failed to create Elasticsearch index for group '%s': %s. "
                "Group creation failed. The group will not work for document indexing/search.",
                config.name,
                ex,
            )
            # Delete the MySQL group since the index creation failed
            await self.mysql_api.groups.delete(name=config.name)
            raise
        await self._upsert_graph_state(
            group_name=config.name,
            status="NOT_BUILT",
            source="none",
        )

        if self.kb_sync is not None:
            self._schedule_kb_sync(self.kb_sync.sync_group_create(config))

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

        # Trigger Ragflow cleanup FIRST while the link record is still intact.
        # Awaiting inline (not fire-and-forget) ensures Ragflow resources are removed
        # even if the Elasticsearch or MySQL deletes fail afterwards.
        if self.kb_sync is not None:
            try:
                await self.kb_sync.sync_group_delete(group_name=name)
            except Exception as exc:
                logging.warning(
                    "Ragflow KB cleanup failed for group '%s' during delete: %s", name, exc
                )

        # Delete the backing vector collection so we do not leave stale
        # Elasticsearch data behind when groups are recreated with the same name.
        try:
            await self.vector_store.adelete_collection(collection_name=name)
        except Exception as ex:
            logging.error(
                "Criadex: failed deleting Elasticsearch index for group '%s': %s",
                name,
                ex,
            )
            raise RuntimeError(
                f"Failed to delete Elasticsearch collection for group '{name}'"
            ) from ex

        # Delete MySQL documents and assets
        await self.mysql_api.assets.delete_all_group_assets(group_id=group_id)
        await self.mysql_api.documents.delete_all(group_id=group_id)

        # Delete group itself
        await self.mysql_api.groups.delete(name=name)
        await self._delete_graph_records(group_name=name)

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
        entry_stream = enumerate(self._iter_file_entries(file_contents=file_contents))

        for batch_number, batch in enumerate(self._batch_iterable(entry_stream, self._ingest_batch_size), start=1):
            for i, (text, metadata) in batch:
                merged_metadata = dict(metadata or {})
                merged_metadata.update(file_metadata)
                merged_metadata.update({
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
                    metadata=merged_metadata
                )

            # Refresh once per batch to reduce Elasticsearch memory churn during large ingests.
            refresh_collection = getattr(self.vector_store, "arefresh_collection", None)
            if callable(refresh_collection):
                await refresh_collection(collection_name=group_name)

            if self._ingest_gc_every_batches and batch_number % self._ingest_gc_every_batches == 0:
                gc.collect()

        await self.mysql_api.documents.insert(document_name=file_name, group_id=group_id)
        await self._invalidate_search_cache(group_name)
        await self.mark_graph_stale(group_name=group_name, reason="content_uploaded")

        if self.kb_sync is not None:
            self._schedule_kb_sync(
                self.kb_sync.sync_document_upload(
                    group_name=group_name,
                    file_name=file_name,
                    file_contents=file_contents,
                )
            )

        return total_tokens

    async def insert_native_file(
        self,
        group_name: str,
        file_name: str,
        file_bytes: bytes,
        strategy: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """Upload a raw file to Ragflow for parsing.

        strategy=None / "GENERIC": raw upload, Ragflow's native parser handles it.
        strategy="ALSYLLABUS" etc.: pre-process locally to UTF-8 text first.
        """
        group_id = await self.get_id(name=group_name)

        if await self.mysql_api.documents.exists(group_id=group_id, document_name=file_name):
            raise DocumentExistsError()

        await self.mysql_api.documents.insert(document_name=file_name, group_id=group_id)
        await self._invalidate_search_cache(group_name)
        await self.mark_graph_stale(group_name=group_name, reason="content_uploaded")

        if self.kb_sync is not None:
            self._schedule_kb_sync(
                self.kb_sync.sync_native_file_upload(
                    group_name=group_name,
                    file_name=file_name,
                    file_bytes=file_bytes,
                    strategy=strategy,
                    content_type=content_type,
                )
            )

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
        await self._invalidate_search_cache(group_name)
        await self.mark_graph_stale(group_name=group_name, reason="content_deleted")

        if self.kb_sync is not None:
            self._schedule_kb_sync(
                self.kb_sync.sync_document_delete(
                    group_name=group_name,
                    document_name=document_name,
                )
            )

    async def update_file(self, group_name: str, file_name: str, file_contents: dict, file_metadata: dict) -> int:
        await self.delete_file(group_name=group_name, document_name=file_name)
        result = await self.insert_file(group_name=group_name, file_name=file_name, file_contents=file_contents, file_metadata=file_metadata)
        await self.mark_graph_stale(group_name=group_name, reason="content_updated")
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

        redis_pool = getattr(self, "_redis_pool", None)
        if redis_pool is not None:
            try:
                await redis_pool.disconnect(inuse_connections=True)
            except Exception:
                pass

        # Give the async loop a moment to close the connection
        await asyncio.sleep(0.25)

    async def _invalidate_search_cache(self, group_name: str) -> None:
        """Invalidate all cached search results for a group (Redis + in-process)."""
        if self._redis_api is not None:
            await self._redis_api.search_results.invalidate_group(group_name)
        if self.cache:
            self.cache.clear()

    async def search(self, group_name: str, query: SearchConfig, top_k=10, query_filter: Optional[dict] = None):
        if not await self.exists(name=group_name):
            raise GroupNotFoundError()

        self.event.emit(Event.SEARCH, query=query)

        if self._redis_api is not None:
            cache_key = self._redis_api.search_results.build_key(
                group_name=group_name, query=query.query, top_k=query.top_k
            )
            cached = await self._redis_api.search_results.get(cache_key)
            if cached is not None:
                from criadex.index.schemas import IndexResponse
                return IndexResponse(**cached)
            results = await self.bot.search(group_name, query.query, top_k=query.top_k, query_filter=query_filter)
            await self._redis_api.search_results.set(cache_key, results)
        else:
            # In-process LRU fallback — key includes group_name to prevent cross-group collisions
            cache_key = f"{group_name}:{query.model_dump_json()}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
            results = await self.bot.search(group_name, query.query, top_k=query.top_k, query_filter=query_filter)
            self.cache.set(cache_key, results)

        return results

    async def _group_documents(self, group_name: str, size: int = 200) -> list[str]:
        if self.vector_store is None or getattr(self.vector_store, "es", None) is None:
            return []

        max_docs = max(1, int(getattr(config, "GRAPH_FALLBACK_MAX_DOCS", 300)))
        max_doc_chars = max(256, int(getattr(config, "GRAPH_FALLBACK_MAX_DOC_CHARS", 4000)))

        def run_search(offset: int, page_size: int):
            index_name = group_name
            if hasattr(self.vector_store, "_to_es_index_name"):
                index_name = self.vector_store._to_es_index_name(group_name)
            return self.vector_store.es.search(
                index=index_name,
                query={"match_all": {}},
                size=page_size,
                from_=offset,
                _source=["text"],
                sort=[{"metadata.updated_at": {"order": "desc"}}],
            )

        collected: list[str] = []
        offset = 0
        page_size = max(1, min(size, max_docs))

        while len(collected) < max_docs:
            remaining = max_docs - len(collected)
            current_page_size = min(page_size, remaining)
            try:
                response = await asyncio.get_running_loop().run_in_executor(
                    None,
                    run_search,
                    offset,
                    current_page_size,
                )
            except ESNotFoundError as exc:
                raise IndexNotFoundError(
                    f"Elasticsearch index for group '{group_name}' not found. "
                    "The group's content index may have been lost. Re-upload content to rebuild the index."
                ) from exc

            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                break

            for hit in hits:
                text = hit.get("_source", {}).get("text", "")
                if not text:
                    continue
                collected.append(str(text)[:max_doc_chars])
                if len(collected) >= max_docs:
                    break

            if len(hits) < current_page_size:
                break

            offset += len(hits)

        return collected

    async def _recover_graph_jobs(self) -> None:
        now = int(time.time() * 1000)
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE GraphBuildJobs
                    SET state='FAILED', error='Service restarted while job was running.', updated_at=%s, finished_at=%s
                    WHERE state IN ('QUEUED', 'RUNNING')
                    """,
                    (now, now),
                )
                await cursor.execute(
                    """
                    UPDATE GroupGraphStates
                    SET status='STALE', error='Service restarted while graph build was in progress.', updated_at=%s
                    WHERE status IN ('QUEUED', 'RUNNING')
                    """,
                    (now,),
                )

    async def _upsert_graph_state(
        self,
        group_name: str,
        status: str,
        source: str,
        node_count: int = 0,
        edge_count: int = 0,
        top_entities: Optional[list[str]] = None,
        fallback_reason: Optional[str] = None,
        error: Optional[str] = None,
        built_at: Optional[int] = None,
    ) -> None:
        now = int(time.time() * 1000)
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO GroupGraphStates
                        (group_name, status, source, node_count, edge_count, top_entities, fallback_reason, error, built_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new
                    ON DUPLICATE KEY UPDATE
                        status=new.status,
                        source=new.source,
                        node_count=new.node_count,
                        edge_count=new.edge_count,
                        top_entities=new.top_entities,
                        fallback_reason=new.fallback_reason,
                        error=new.error,
                        built_at=new.built_at,
                        updated_at=new.updated_at
                    """,
                    (
                        group_name,
                        status,
                        source,
                        node_count,
                        edge_count,
                        json.dumps(top_entities or []),
                        fallback_reason,
                        error,
                        built_at,
                        now,
                    ),
                )

    async def _read_graph_state(self, group_name: str) -> dict:
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT status, source, node_count, edge_count, top_entities, fallback_reason, error, built_at, updated_at
                    FROM GroupGraphStates
                    WHERE group_name=%s
                    """,
                    (group_name,),
                )
                row = await cursor.fetchone()
        if row is None:
            return {
                "status": "NOT_BUILT",
                "source": "none",
                "node_count": 0,
                "edge_count": 0,
                "top_entities": [],
                "fallback_reason": None,
                "error": None,
                "built_at": None,
                "updated_at": None,
            }
        top_entities = []
        if row[4]:
            try:
                top_entities = json.loads(row[4]) if isinstance(row[4], str) else row[4]
            except Exception:
                top_entities = []
        return {
            "status": row[0],
            "source": row[1] or "none",
            "node_count": int(row[2] or 0),
            "edge_count": int(row[3] or 0),
            "top_entities": top_entities or [],
            "fallback_reason": row[5],
            "error": row[6],
            "built_at": row[7],
            "updated_at": row[8],
        }

    async def _delete_graph_records(self, group_name: str) -> None:
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("DELETE FROM GraphBuildJobs WHERE group_name=%s", (group_name,))
                await cursor.execute("DELETE FROM GroupGraphStates WHERE group_name=%s", (group_name,))

    async def _insert_graph_job(self, group_name: str) -> str:
        job_id = str(uuid.uuid4())
        now = int(time.time() * 1000)
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO GraphBuildJobs
                        (job_id, group_name, state, source, progress, created_at, updated_at)
                    VALUES (%s, %s, 'QUEUED', 'none', 0, %s, %s)
                    """,
                    (job_id, group_name, now, now),
                )
        await self._upsert_graph_state(group_name=group_name, status="QUEUED", source="none")
        return job_id

    async def _latest_graph_job(self, group_name: str) -> Optional[dict]:
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT job_id, group_name, state, source, progress, error, metadata, created_at, updated_at, started_at, finished_at
                    FROM GraphBuildJobs
                    WHERE group_name=%s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (group_name,),
                )
                row = await cursor.fetchone()
        if row is None:
            return None
        metadata = {}
        if row[6]:
            try:
                metadata = json.loads(row[6]) if isinstance(row[6], str) else row[6]
            except Exception:
                metadata = {}
        return {
            "job_id": row[0],
            "group_name": row[1],
            "state": row[2],
            "source": row[3] or "none",
            "progress": int(row[4] or 0),
            "error": row[5],
            "metadata": metadata or {},
            "created_at": row[7],
            "updated_at": row[8],
            "started_at": row[9],
            "finished_at": row[10],
        }

    async def _job_by_id(self, job_id: str) -> Optional[dict]:
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT job_id, group_name, state, source, progress, error, metadata, created_at, updated_at, started_at, finished_at
                    FROM GraphBuildJobs
                    WHERE job_id=%s
                    """,
                    (job_id,),
                )
                row = await cursor.fetchone()
        if row is None:
            return None
        metadata = {}
        if row[6]:
            try:
                metadata = json.loads(row[6]) if isinstance(row[6], str) else row[6]
            except Exception:
                metadata = {}
        return {
            "job_id": row[0],
            "group_name": row[1],
            "state": row[2],
            "source": row[3] or "none",
            "progress": int(row[4] or 0),
            "error": row[5],
            "metadata": metadata or {},
            "created_at": row[7],
            "updated_at": row[8],
            "started_at": row[9],
            "finished_at": row[10],
        }

    async def _update_graph_job(
        self,
        job_id: str,
        state: str,
        source: str = "none",
        progress: int = 0,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
        started_at: Optional[int] = None,
        finished_at: Optional[int] = None,
    ) -> None:
        now = int(time.time() * 1000)
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE GraphBuildJobs
                    SET state=%s,
                        source=%s,
                        progress=%s,
                        error=%s,
                        metadata=%s,
                        updated_at=%s,
                        started_at=COALESCE(%s, started_at),
                        finished_at=COALESCE(%s, finished_at)
                    WHERE job_id=%s
                    """,
                    (
                        state,
                        source,
                        progress,
                        error,
                        json.dumps(metadata or {}),
                        now,
                        started_at,
                        finished_at,
                        job_id,
                    ),
                )

    async def mark_graph_stale(self, group_name: str, reason: str = "content_changed") -> None:
        if not await self.exists(name=group_name):
            return
        await self._upsert_graph_state(
            group_name=group_name,
            status="STALE",
            source="none",
            fallback_reason=reason,
        )

    async def _run_graph_build_job(self, job_id: str, group_name: str) -> None:
        started_at = int(time.time() * 1000)
        await self._update_graph_job(
            job_id=job_id,
            state="RUNNING",
            source="none",
            progress=10,
            started_at=started_at,
        )
        await self._upsert_graph_state(group_name=group_name, status="RUNNING", source="none")

        fallback_error = None
        try:
            if config.GRAPH_RAG_ENABLED:
                await self.graph_rag_client.build_graph(group_name=group_name)
                ragflow_status = await self.graph_rag_client.graph_status(group_name=group_name)
                built_at = int(time.time() * 1000)
                node_count = int(ragflow_status.get("node_count", 0) or 0)
                edge_count = int(ragflow_status.get("edge_count", 0) or 0)
                top_entities = ragflow_status.get("top_entities", []) or []
                await self._upsert_graph_state(
                    group_name=group_name,
                    status="READY",
                    source="ragflow",
                    node_count=node_count,
                    edge_count=edge_count,
                    top_entities=top_entities,
                    built_at=built_at,
                )
                await self._update_graph_job(
                    job_id=job_id,
                    state="READY",
                    source="ragflow",
                    progress=100,
                    metadata={"ragflow_status": ragflow_status},
                    finished_at=int(time.time() * 1000),
                )
                return
        except Exception as ex:
            fallback_error = str(ex)

        if not config.GRAPH_RAG_FALLBACK_ENABLED:
            await self._upsert_graph_state(
                group_name=group_name,
                status="FAILED",
                source="none",
                error=fallback_error,
            )
            await self._update_graph_job(
                job_id=job_id,
                state="FAILED",
                source="none",
                progress=100,
                error=fallback_error,
                finished_at=int(time.time() * 1000),
            )
            return

        documents = await self._group_documents(group_name=group_name)
        local_result = self.graph_store.build(group_name=group_name, documents=documents)
        await self._upsert_graph_state(
            group_name=group_name,
            status="READY",
            source="fallback",
            node_count=local_result["node_count"],
            edge_count=local_result["edge_count"],
            top_entities=local_result["top_entities"],
            fallback_reason=fallback_error or "ragflow_unavailable",
            built_at=int(time.time() * 1000),
        )
        await self._update_graph_job(
            job_id=job_id,
            state="READY",
            source="fallback",
            progress=100,
            metadata={"fallback_reason": fallback_error or "ragflow_unavailable"},
            finished_at=int(time.time() * 1000),
        )

    async def build_graph(self, group_name: str, force: bool = False) -> dict:
        if not await self.exists(name=group_name):
            raise GroupNotFoundError()

        latest_job = await self._latest_graph_job(group_name=group_name)
        if latest_job and latest_job["state"] in {"QUEUED", "RUNNING"} and not force:
            return latest_job

        job_id = await self._insert_graph_job(group_name=group_name)
        if config.APP_MODE == AppMode.TESTING:
            await self._run_graph_build_job(job_id=job_id, group_name=group_name)
        else:
            task = asyncio.create_task(self._run_graph_build_job(job_id=job_id, group_name=group_name))
            self._graph_job_tasks[job_id] = task
            task.add_done_callback(lambda _t, tracked_job_id=job_id: self._graph_job_tasks.pop(tracked_job_id, None))

        job = await self._job_by_id(job_id=job_id)
        return job or {"job_id": job_id, "group_name": group_name, "state": "QUEUED"}

    async def graph_status(self, group_name: str, job_id: Optional[str] = None) -> dict:
        if not await self.exists(name=group_name):
            raise GroupNotFoundError()

        state = await self._read_graph_state(group_name=group_name)
        job = await self._job_by_id(job_id=job_id) if job_id else await self._latest_graph_job(group_name=group_name)
        return {
            "group_name": group_name,
            "graph": state,
            "job": job,
        }

    async def graph_search(
        self,
        group_name: str,
        query: SearchConfig,
        max_hops: int = 1,
        max_expansion_terms: int = 8,
        auto_build: bool = False
    ):
        if not await self.exists(name=group_name):
            raise GroupNotFoundError()

        status_payload = await self.graph_status(group_name=group_name)
        graph_state = status_payload["graph"]
        job = status_payload.get("job")

        if auto_build and graph_state["status"] in {"NOT_BUILT", "STALE", "FAILED"}:
            job = await self.build_graph(group_name=group_name, force=graph_state["status"] == "FAILED")
            status_payload = await self.graph_status(group_name=group_name, job_id=job.get("job_id"))
            graph_state = status_payload["graph"]

        start_ms = int(time.time() * 1000)
        expanded_terms: list[str] = []
        effective_query = query.query
        source = graph_state["source"] if graph_state["source"] != "none" else "standard"
        fallback_reason = graph_state.get("fallback_reason")

        if config.GRAPH_RAG_ENABLED and graph_state["status"] == "READY":
            try:
                ragflow_result = await self.graph_rag_client.graph_search(
                    group_name=group_name,
                    query=query.query,
                    max_hops=max_hops,
                    max_expansion_terms=max_expansion_terms,
                )
                expanded_terms = (
                    ragflow_result.get("expanded_terms")
                    or ragflow_result.get("related_terms")
                    or ragflow_result.get("terms")
                    or []
                )
                if expanded_terms:
                    effective_query = f"{query.query}\nRelated terms: {', '.join(expanded_terms[:max_expansion_terms])}"
                source = "ragflow"
                fallback_reason = None
            except Exception as ex:
                fallback_reason = str(ex)
                # Ensure fallback path can activate when ragflow graph-search fails.
                source = "standard"

        if source != "ragflow" and config.GRAPH_RAG_FALLBACK_ENABLED:
            if graph_state["status"] != "READY" or graph_state["source"] != "fallback":
                documents = await self._group_documents(group_name=group_name)
                local_result = self.graph_store.build(group_name=group_name, documents=documents)
                await self._upsert_graph_state(
                    group_name=group_name,
                    status="READY",
                    source="fallback",
                    node_count=local_result["node_count"],
                    edge_count=local_result["edge_count"],
                    top_entities=local_result["top_entities"],
                    fallback_reason=fallback_reason or "ragflow_graph_search_failed",
                    built_at=int(time.time() * 1000),
                )
                graph_state = await self._read_graph_state(group_name=group_name)

            expanded_terms = self.graph_store.expand_query(
                group_name=group_name,
                query=query.query,
                max_hops=max_hops,
                max_terms=max_expansion_terms,
            )
            if expanded_terms:
                effective_query = f"{query.query}\nRelated terms: {', '.join(expanded_terms[:max_expansion_terms])}"
            source = "fallback"

        graph_query = query.model_copy(update={"query": effective_query})
        response = await self.search(group_name=group_name, query=graph_query)

        graph_metadata = {
            "status": graph_state["status"],
            "source": source,
            "expanded_terms": expanded_terms,
            "fallback_reason": fallback_reason,
            "max_hops": max_hops,
            "max_expansion_terms": max_expansion_terms,
            "job_id": job.get("job_id") if isinstance(job, dict) else None,
            "latency_ms": int(time.time() * 1000) - start_ms,
        }
        return response, graph_metadata

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

    async def exists_cohere_model(self, model_id: int) -> bool:
        """
        Check if a Cohere model exists by ID.
        
        :param model_id: The model ID
        :return: Whether the model exists
        """
        return await self.mysql_api.cohere_models.exists(model_id=model_id)

    async def exists_generic_model(self, model_id: int) -> bool:
        """Check if a generic provider model exists by ID."""
        return await self.mysql_api.generic_models.exists(model_id=model_id)

    async def exists_model(self, model_id: int) -> bool:
        """Check if a model exists in any provider registry table."""
        if model_id <= 0:
            return False
        if await self.exists_azure_model(model_id):
            return True
        if await self.exists_cohere_model(model_id):
            return True
        return await self.exists_generic_model(model_id)

    async def about_azure_model(self, model_id: int) -> AzureModelsModel:
        """
        Retrieve an Azure model by ID or raise if not found.
        """
        model = await self.mysql_api.azure_models.retrieve(model_id=model_id)
        if model is None:
            from criadex.schemas import ModelNotFoundError
            raise ModelNotFoundError()
        return model

    async def list_azure_models(self) -> list[AzureModelsModel]:
        return await self.mysql_api.azure_models.get_all()

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

    async def list_cohere_models(self) -> list[CohereModelsModel]:
        return await self.mysql_api.cohere_models.get_all()

    async def list_generic_models(self) -> list[GenericModelsModel]:
        return await self.mysql_api.generic_models.get_all()

    async def sync_ragflow_models(self, tenant_id: Optional[str] = None) -> dict[str, int]:
        from criadex.index.ragflow_objects.model_sync import sync_ragflow_models
        return await sync_ragflow_models(self.mysql_api, tenant_id=tenant_id)

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