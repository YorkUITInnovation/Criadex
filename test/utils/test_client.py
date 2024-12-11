from __future__ import annotations

import os
import typing
from contextlib import asynccontextmanager
# Change the working directory for .env loading purposes
from pathlib import Path
from typing import AsyncGenerator
from typing import Type, Optional

import httpx
import pytest
import pytest_asyncio
from starlette.testclient import TestClient

if typing.TYPE_CHECKING:
    from app.controllers.schemas import APIResponse

    T = typing.TypeVar("T", bound=APIResponse)


class CriaTestClient(TestClient):

    # noinspection PyProtectedMember
    def get_json(
            self,
            url: httpx._types.URLTypes,
            *,
            params: httpx._types.QueryParamTypes | None = None,
            headers: httpx._types.HeaderTypes | None = None,
            cookies: httpx._types.CookieTypes | None = None,
            auth: httpx._types.AuthTypes | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
            follow_redirects: bool | None = None,
            allow_redirects: bool | None = None,
            timeout: httpx._types.TimeoutTypes | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
            extensions: dict[str, typing.Any] | None = None,
            apply_shape: Optional[Type["T"]] = None,
            apply_shape_require_status: Optional[int] = None,
            apply_shape_require_code: Optional[str] = None
    ) -> dict | "T":
        response = self.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            allow_redirects=allow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

        json_data = response.json()
        if apply_shape:
            return assert_response_shape(
                json_data,
                custom_shape=apply_shape,
                require_status=apply_shape_require_status,
                require_code=apply_shape_require_code
            )
        return json_data


@asynccontextmanager
async def load_client() -> AsyncGenerator[CriaTestClient, None]:
    """
    Load the API as a TestClient instance for use in pytest

    :return: TestClient instance

    """

    # Swap to directory with __main__.py
    app_dir: Path = Path(__file__).parent.parent.parent.joinpath("./app").resolve().absolute()
    os.chdir(str(app_dir))

    # Env as base project path
    os.environ['DOTENV_PATH'] = os.environ.get('DOTENV_PATH', str(app_dir.parent))

    from app.core.app import CriadexAPI
    app = CriadexAPI.create()
    await app._initialize(app)

    # Yield the client
    with CriaTestClient(app) as client:
        try:
            yield client
        finally:
            await app.criadex.shutdown()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[CriaTestClient, None]:
    """
    Get the test client

    :return: Test client
    """

    async with load_client() as test_client:
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


@pytest.fixture
def sample_document_index() -> str:
    """
    Get the document test group

    :return: Document test group

    """

    return os.environ.get('TEST_DOCUMENT_GROUP', 'test-document-index')


@pytest.fixture
def sample_question_index() -> str:
    """
    Get the test question index

    :return: Test question index

    """

    return os.environ.get('TEST_QUESTION_INDEX', 'test-question-index')


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


def assert_response_shape(
        response: dict | None,
        *,
        require_status: int | None = 200,
        require_code: str | None = "SUCCESS",
        custom_shape: Type["T"] | None = None
) -> "T":
    """
    Assert the response shape is correct

    :param response: The response
    :param require_status: The required status code #
    :param require_code: The required code
    :param custom_shape: Custom shape class to apply
    :return: The assertion

    """

    assert response is not None, "Response is None. Ensure the API is running."

    try:

        assert isinstance(response, dict), "Response is not a dictionary"
        assert 'status' in response, "Response does not contain a 'status' key"
        assert 'code' in response, "Response does not contain a 'code' key"
        assert 'message' in response, "Response does not contain a 'message' key"
        assert 'timestamp' in response, "Response does not contain a 'timestamp' key"

        # Apply a custom shape if provided
        api_response = custom_shape(**response) if custom_shape else APIResponse(**response)

        if require_status:
            assert api_response.status == require_status, f"Status is {api_response.status}, expected {require_status}"

        if require_code:
            assert api_response.code == require_code, f"Code is {api_response.code}, expected {require_code}"

    except Exception as e:
        raise AssertionError(f"Response shape is incorrect (does not match APIResponse): {e}")

    return api_response


@pytest.fixture
def sample_master_headers() -> dict:
    """
    Get the headers for a master key

    :return: The headers

    """

    return {
        'X-Api-Key': _get_master_credentials()
    }
