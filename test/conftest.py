import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import uuid

# we need to import CriaTestClient from the other file
from .utils.test_client import CriaTestClient

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@asynccontextmanager
async def load_client(sample_document_index, sample_question_index) -> AsyncGenerator[CriaTestClient, None]:
    """
    Load the API as a TestClient instance for use in pytest

    :return: TestClient instance

    """

    # Swap to directory with __main__.py
    app_dir: Path = Path(__file__).parent.parent.joinpath("./app").resolve().absolute()
    os.chdir(str(app_dir))

    # Env as base project path
    os.environ['ENV_PATH'] = os.environ.get('ENV_PATH', str(app_dir.parent))

    from app.core.app import CriadexAPI
    app = CriadexAPI.create()

    # Yield the client
    with CriaTestClient(app) as client:
        try:
            # Ensure required test groups exist after app startup via API calls (avoid cross-loop DB calls)
            document_group: str = os.environ.get('TEST_DOCUMENT_GROUP', 'test-document-index')
            question_group: str = os.environ.get('TEST_QUESTION_INDEX', 'test-question-index')
            # Use model IDs that exist from schema.sql defaults
            llm_id: int = int(os.environ.get('TEST_LLM_ID', '1'))
            embed_id: int = int(os.environ.get('TEST_EMBEDDING_ID', '2'))
            rerank_id: int = int(os.environ.get('TEST_RERANKER_ID', '1'))
            non_master_key: str = os.environ.get('TEST_NON_MASTER_KEY', 'password-nomaster')

            headers = {'X-Api-Key': os.environ.get('TEST_MASTER_KEY', 'password')}

            def ensure_group(name: str, type_key: str) -> None:
                payload = {
                    "type": type_key,
                    "llm_model_id": llm_id,
                    "embedding_model_id": embed_id,
                    "rerank_model_id": rerank_id,
                }
                # Try create; if exists, ignore
                resp = client.post(f"/groups/{name}/create", headers=headers, json=payload)
                # 200 or 409 are acceptable for idempotent setup
                status = resp.json().get("status") if resp is not None else None
                if status not in (200, 409):
                    raise AssertionError(f"Failed to ensure group '{name}' exists for tests")

            ensure_group(sample_document_index, "DOCUMENT")
            ensure_group(sample_question_index, "QUESTION")

            # Ensure non-master key exists for group_auth tests
            key_payload = {"master": False}
            resp = client.post(f"/auth/{non_master_key}/create", headers={'X-Api-Key': os.environ.get('TEST_MASTER_KEY', 'password')}, json=key_payload)
            # 200 or 409 are fine (created or duplicate)
            _status = resp.json().get("status") if resp is not None else None
            assert _status in (200, 409), "Failed to create or identify test non-master API key"
            yield client
        finally:
            await app.criadex.shutdown()


@pytest_asyncio.fixture(scope="session")
async def setup_database(event_loop):
    """
    Set up the database for the test session.
    """
    from app.core import config
    import aiomysql

    if os.environ.get('APP_API_MODE', 'TESTING') == 'TESTING':
        host = '127.0.0.1'
        db_name = 'criadex_test'
    else:
        host = os.environ.get('MYSQL_HOST') or config.MYSQL_CREDENTIALS.host
        db_name = os.environ.get('MYSQL_DATABASE', 'criadex')


    # Clean the database
    async with aiomysql.connect(
        host=host,
        port=config.MYSQL_CREDENTIALS.port,
        user=config.MYSQL_CREDENTIALS.username,
        password=config.MYSQL_CREDENTIALS.password,
    ) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            await cursor.execute(f"CREATE DATABASE {db_name}")


@pytest_asyncio.fixture(scope="session")
async def populate_models(setup_database):
    """
    Populate the database with dummy model data for tests.
    """
    from app.core import config
    import aiomysql

    if os.environ.get('APP_API_MODE', 'TESTING') == 'TESTING':
        host = '127.0.0.1'
        db_name = 'criadex_test'
    else:
        host = os.environ.get('MYSQL_HOST') or config.MYSQL_CREDENTIALS.host
        db_name = os.environ.get('MYSQL_DATABASE', 'criadex')

    # This is a bit of a hack; ideally the app would create the tables.
    # We need to ensure the tables exist before we can insert data.
    # Running the app's initialization logic here.
    from app.core.app import CriadexAPI
    app = CriadexAPI.create()
    await app.criadex.initialize()
    await app.criadex.shutdown() # Shutdown to release connections

    async with aiomysql.connect(
        host=host,
        port=config.MYSQL_CREDENTIALS.port,
        user=config.MYSQL_CREDENTIALS.username,
        password=config.MYSQL_CREDENTIALS.password,
        db=db_name
    ) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO AzureModels (id, api_resource, api_version, api_key, api_deployment, api_model)
                VALUES
                (1, 'test-resource', '2023-05-15', 'test-key', 'test-deployment', 'gpt-4'),
                (2, 'test-resource-2', '2023-05-15', 'test-key-2', 'test-deployment-2', 'text-embedding-ada-002')
            """)
            await cursor.execute("""
                INSERT INTO CohereModels (id, api_key, api_model)
                VALUES
                (1, 'test-cohere-key', 'rerank-english-v2.0'),
                (3, 'test-cohere-key-3', 'rerank-english-v2.0')
            """)
        await conn.commit()


@pytest_asyncio.fixture(scope="session")
async def client(populate_models, sample_document_index, sample_question_index) -> AsyncGenerator[CriaTestClient, None]:
    """
    Get the test client

    :return: Test client
    """

    async with load_client(sample_document_index, sample_question_index) as test_client:
        yield test_client


def _get_master_credentials() -> str:
    """
    Get the test API key

    :return: Test API key

    """

    return os.environ.get('TEST_MASTER_KEY', 'password')


def _get_non_master_credentials() -> str:
    """
    Get the test NON-master API key

    :return: The non-master key

    """

    return os.environ.get('TEST_NON_MASTER_KEY', 'password-nomaster')


@pytest.fixture
def sample_master_key() -> str:
    """
    Get the test API key

    :return: Test API key

    """

    return _get_master_credentials()


@pytest.fixture
def sample_non_master_key() -> str:
    """
    Get the test non-master API key

    :return: The test non-master API key

    """

    return _get_non_master_credentials()


@pytest.fixture(scope="session")
def sample_document_index() -> str:
    """
    Get the document test group

    :return: Document test group

    """

    return "test-document-index-" + str(uuid.uuid4())


@pytest.fixture(scope="session")
def sample_question_index() -> str:
    """
    Get the test question index

    :return: Test question index

    """

    return "test-question-index-" + str(uuid.uuid4())


@pytest.fixture
def sample_llm_id() -> int:
    """Sample LLM Id"""

    return int(os.environ.get('TEST_LLM_ID', '1'))


@pytest.fixture
def sample_embedding_id() -> int:
    """Sample LLM Id"""

    return int(os.environ.get('TEST_EMBEDDING_ID', '2'))


@pytest.fixture
def sample_reranker_id() -> int:
    """Sample LLM Id"""

    return int(os.environ.get('TEST_RERANKER_ID', '3'))


@pytest.fixture
def sample_master_headers() -> dict:
    """
    Get the headers for a master key

    :return: The headers

    """

    return {
        'X-Api-Key': _get_master_credentials()
    }

@pytest.fixture
def sample_non_master_headers() -> dict:
    """
    Get the headers for a non-master key

    :return: The headers

    """

    return {
        'X-Api-Key': _get_non_master_credentials()
    }
