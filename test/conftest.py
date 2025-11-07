import os
import asyncio
import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import MagicMock
from elasticsearch import Elasticsearch
from _pytest.monkeypatch import MonkeyPatch

import json
from .utils.test_client import CriaTestClient
from .utils.misc_utils import assert_does_not_exist_index

_active_aiomysql_connections = []

# Original aiomysql.connect function
_original_aiomysql_connect = None

# Monkeypatch aiomysql.connect to track connections
def _monkeypatch_aiomysql_connect():
    global _original_aiomysql_connect
    import aiomysql
    _original_aiomysql_connect = aiomysql.connect

    async def new_connect(*args, **kwargs):
        conn = await _original_aiomysql_connect(*args, **kwargs)
        _active_aiomysql_connections.append(conn)
        return conn
    aiomysql.connect = new_connect

# Unmonkeypatch aiomysql.connect
def _unmonkeypatch_aiomysql_connect():
    global _original_aiomysql_connect
    if _original_aiomysql_connect:
        import aiomysql
        aiomysql.connect = _original_aiomysql_connect
        _original_aiomysql_connect = None


# ───────────────────────────────
#   Pytest Elasticsearch Mock
# ───────────────────────────────
def pytest_configure(config):
    
    """Configure session-scoped mocks and monkeypatches."""
    os.environ["MYSQL_DATABASE"] = "criadex_test"

    mock_es = MagicMock(spec=Elasticsearch)
    mock_es.indices = MagicMock()
    mock_es.indices.exists.return_value = True
    mock_es.indices.create.return_value = {'acknowledged': True}
    def mock_index(index, document, id, **kwargs):
        if index not in mock_es._data:
            mock_es._data[index] = {}
        mock_es._data[index][id] = document
        return {'result': 'created'}
    mock_es.index.side_effect = mock_index
    mock_es.delete.return_value = {'result': 'deleted'}
    mock_es.delete_by_query.return_value = {'deleted': 1}
    mock_es._data = {}

    def mock_search_impl(**kwargs):
        index = kwargs.get('index')
        body = kwargs.get('body')
        size = kwargs.get('size')
        sort = kwargs.get('sort')

        all_docs = []
        for doc_id, doc_content in mock_es._data.get(index, {}).items():
            all_docs.append({'_source': doc_content, '_id': doc_id})

        

        # Apply sorting
        if sort:
            # Assuming sort is a list of dictionaries, e.g., [{"metadata.updated_at": {"order": "desc"}}]
            # Or a dictionary like {"metadata.updated_at": {"order": "desc"}}
            # Let's handle both cases.
            if isinstance(sort, list) and len(sort) > 0:
                sort_criteria = sort[0]
            elif isinstance(sort, dict):
                sort_criteria = sort
            else:
                sort_criteria = None

            if sort_criteria:
                sort_field = list(sort_criteria.keys())[0] # e.g., "metadata.updated_at"
                sort_order = sort_criteria[sort_field]["order"] # e.g., "desc"

                # Extract nested field for sorting
                def get_sort_value(hit, field_path):
                    parts = field_path.split('.')
                    value = hit['_source']
                    for part in parts:
                        value = value.get(part)
                        if value is None:
                            return None # Handle missing nested fields
                    return value

                all_docs.sort(
                    key=lambda hit: get_sort_value(hit, sort_field),
                    reverse=(sort_order == "desc")
                )
        

        hits = all_docs[:size] # Apply size/top_k limit after sorting

        return {'hits': {'hits': hits}}

    mock_es.search = MagicMock(side_effect=mock_search_impl)

    config._mock_elasticsearch_client = mock_es
    config._monkeypatch_session = MonkeyPatch()
    config._monkeypatch_session.setattr(
        "criadex.index.ragflow_objects.vector_store.RagflowVectorStore.__init__",
        lambda self, *_, **__: setattr(self, 'es', mock_es)
    )
    
    _monkeypatch_aiomysql_connect() # Monkeypatch aiomysql.connect here


def pytest_unconfigure(config):
    
    """Undo monkeypatching at the end of the session."""
    config._monkeypatch_session.undo()
    _unmonkeypatch_aiomysql_connect() # Unmonkeypatch aiomysql.connect here
    


@pytest.fixture(scope="session")
def mock_elasticsearch_client(request):
    """Return the session-scoped mock Elasticsearch client."""
    return request.config._mock_elasticsearch_client


# ───────────────────────────────
#   Event Loop Fixture
# ───────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    """Create and close an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()

    # Custom exception handler to suppress "Event loop is closed" RuntimeError
    def custom_exception_handler(loop, context):
        exception = context.get("exception")
        if isinstance(exception, RuntimeError) and "Event loop is closed" in str(exception):
            return # Suppress this specific error
        loop.default_exception_handler(context) # Call default handler for other exceptions

    loop.set_exception_handler(custom_exception_handler)

    yield loop
    # Add a small delay before closing the loop
    try:
        # Close all tracked aiomysql connections
        
        for conn in _active_aiomysql_connections:
            if not conn.closed:
                loop.run_until_complete(conn.close())
        # Explicitly clear references to aid garbage collection
        _active_aiomysql_connections.clear()
        # Also try to force garbage collection, though not guaranteed to work
        import gc
        gc.collect()
        

        _cancel_all_tasks(loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(asyncio.sleep(0.1)) # Small delay
    finally:
        try:
            loop.close()
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                pass # Suppress this specific error
            else:
                raise



def _cancel_all_tasks(loop):
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'unhandled exception during asyncio.run() shutdown',
                'exception': task.exception(),
                'task': task,
            })


# ───────────────────────────────
#   Load CriaTestClient
# ───────────────────────────────
@asynccontextmanager
async def load_client(sample_document_index, sample_question_index, monkeypatch_session, mock_es_client) -> AsyncGenerator[CriaTestClient, None]:
    """Load the Criadex API test client."""
    app_dir = Path(__file__).parent.parent.joinpath("app").resolve()
    os.chdir(str(app_dir))
    os.environ.setdefault('ENV_PATH', str(app_dir.parent))

    from app.core.app import CriadexAPI
    app = CriadexAPI.create()

    with CriaTestClient(app) as client:
        try:
            headers = {'X-Api-Key': os.environ.get('TEST_MASTER_KEY', 'password')}
            non_master_key = os.environ.get('TEST_NON_MASTER_KEY', 'password-nomaster')

            # Default IDs
            llm_id = int(os.environ.get('TEST_LLM_ID', '1'))
            embed_id = int(os.environ.get('TEST_EMBEDDING_ID', '2'))
            rerank_id = int(os.environ.get('TEST_RERANKER_ID', '1'))

            def ensure_group(name: str, type_key: str):
                payload = {
                    "type": type_key,
                    "llm_model_id": llm_id,
                    "embedding_model_id": embed_id,
                    "rerank_model_id": rerank_id,
                }
                resp = client.post(f"/groups/{name}/create", headers=headers, json=payload)
                status = resp.json().get("status") if resp else None
                if status not in (200, 409):
                    raise AssertionError(f"Failed to ensure group '{name}' exists for tests")

            # Ensure groups exist
            ensure_group(sample_document_index, "DOCUMENT")
            ensure_group(sample_question_index, "QUESTION")

            # Ensure non-master API key exists
            key_payload = {"master": False}
            resp = client.post(
                f"/auth/{non_master_key}/create",
                headers=headers,
                json=key_payload,
            )
            assert resp.json().get("status") in (200, 409), "Failed to create test API key"

            # Mock GET /groups/{index}/exists
            _original_client_get = client.get # Store the original method

            def mock_client_get(url, *args, **kwargs):
                if "/exists" in url:
                    index_name = url.split("/")[-2]
                    exists = index_name in mock_es_client._data
                    return MagicMock(json=lambda: {"status": 200, "code": "SUCCESS", "message": "", "timestamp": 123, "exists": exists, "nodes": [], "assets": [], "search_units": 1})
                return _original_client_get(url, *args, **kwargs) # Call the stored original method

            monkeypatch_session.setattr(client, "get", mock_client_get)

            yield client

        finally:
            await assert_does_not_exist_index(client, headers, sample_document_index)
            await assert_does_not_exist_index(client, headers, sample_question_index)


# ───────────────────────────────
#   Database Setup / Populate
# ───────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create a clean test database."""
    import aiomysql
    from app.core import config

    host = os.environ.get('MYSQL_HOST', '127.0.0.1')
    db_name = 'criadex_test'

    conn = await aiomysql.connect(
        host=host,
        port=config.MYSQL_CREDENTIALS.port,
        user=config.MYSQL_CREDENTIALS.username,
        password=config.MYSQL_CREDENTIALS.password,
    )
    _active_aiomysql_connections.append(conn)

    async with conn.cursor() as cursor:
        await cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        await cursor.execute(f"CREATE DATABASE {db_name}")
        await cursor.execute(f"USE {db_name}")

        with open("criadex/database/schema.sql") as f:
            schema = f.read()
            for statement in schema.split(";"):
                if statement.strip():
                    await cursor.execute(statement)

        with open("app/core/database/schema.sql") as f:
            schema = f.read()
            for statement in schema.split(";"):
                if statement.strip():
                    await cursor.execute(statement)

    yield
    # Connection will be closed by the event_loop fixture's cleanup


@pytest_asyncio.fixture(scope="session")
async def db_connection(setup_database):
    import aiomysql
    from app.core import config

    host = os.environ.get('MYSQL_HOST', '127.0.0.1')
    db_name = 'criadex_test' if os.environ.get('APP_API_MODE', 'TESTING') == 'TESTING' else os.environ.get('MYSQL_DATABASE', 'criadex')

    conn = await aiomysql.connect(
        host=host,
        port=config.MYSQL_CREDENTIALS.port,
        user=config.MYSQL_CREDENTIALS.username,
        password=config.MYSQL_CREDENTIALS.password,
        db=db_name
    )
    _active_aiomysql_connections.append(conn)
    yield conn

@pytest_asyncio.fixture(scope="session")
async def criadex_app(request, populate_models): # Add request to access config
    """Create and initialize the CriadexAPI app."""
    from app.core.app import CriadexAPI
    app = CriadexAPI.create()
    await app.criadex.initialize()
    request.config._criadex_app = app # Store app in config for pytest_unconfigure
    yield app
    # Explicitly close aiomysql pool before app shutdown
    if app.criadex.mysql_pool:
        app.criadex.mysql_pool.close()
        await app.criadex.mysql_pool.wait_closed()
    await app.criadex.shutdown() # Ensure app shutdown is called


@pytest_asyncio.fixture(scope="session")
async def populate_models(db_connection): # Add criadex_app as a dependency
    """Populate dummy model data for tests."""
    async with db_connection.cursor() as cursor:
        await cursor.execute("""
            INSERT INTO AzureModels (id, api_resource, api_version, api_key, api_deployment, api_model)
            VALUES
            (1, 'test-resource', '2023-05-15', 'test-key', 'test-deployment', 'gpt-4'),
            (2, 'test-resource-2', '2023-05-15', 'test-key-2', 'test-deployment-2', 'text-embedding-ada-002')
            ON DUPLICATE KEY UPDATE id=id;
        """)
        await cursor.execute("""
            INSERT INTO CohereModels (id, api_key, api_model)
            VALUES
            (1, 'test-cohere-key', 'rerank-english-v2.0'),
            (3, 'test-cohere-key-3', 'rerank-english-v2.0')
            ON DUPLICATE KEY UPDATE id=id;
        """)
        await db_connection.commit()
    yield


# ───────────────────────────────
#   Test Client Fixture
# ───────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def client(populate_models, sample_document_index, sample_question_index, request) -> AsyncGenerator[CriaTestClient, None]:
    """Provide a ready-to-use CriaTestClient."""
    async with load_client(
        sample_document_index,
        sample_question_index,
        request.config._monkeypatch_session,
        request.config._mock_elasticsearch_client
    ) as test_client:
        yield test_client


# ───────────────────────────────
#   Helper Fixtures & Constants
# ───────────────────────────────
def _get_env_or_default(var: str, default: str) -> str:
    return os.environ.get(var, default)


@pytest.fixture
def sample_master_key() -> str:
    return _get_env_or_default('TEST_MASTER_KEY', 'password')


@pytest.fixture
def sample_non_master_key() -> str:
    return _get_env_or_default('TEST_NON_MASTER_KEY', 'password-nomaster')


@pytest.fixture(scope="session")
def sample_document_index() -> str:
    return f"test-document-index-{uuid.uuid4()}"


@pytest.fixture(scope="session")
def sample_question_index() -> str:
    return f"test-question-index-{uuid.uuid4()}"


@pytest.fixture
def sample_llm_id() -> int:
    return int(_get_env_or_default('TEST_LLM_ID', '1'))


@pytest.fixture
def sample_embedding_id() -> int:
    return int(_get_env_or_default('TEST_EMBEDDING_ID', '2'))


@pytest.fixture
def sample_reranker_id() -> int:
    return int(_get_env_or_default('TEST_RERANKER_ID', '3'))


@pytest.fixture
def sample_master_headers(sample_master_key) -> dict:
    return {'X-Api-Key': sample_master_key}


@pytest.fixture
def sample_non_master_headers(sample_non_master_key) -> dict:
    return {'X-Api-Key': sample_non_master_key}
