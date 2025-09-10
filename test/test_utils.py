import pytest

from .utils.test_client import CriaTestClient


@pytest.mark.asyncio
async def test_client_fixture(client: CriaTestClient) -> None:
    """
    Test the client fixture to ensure it is loaded correctly.

    """

    assert isinstance(client, CriaTestClient), "Client is not an instance of CriaTestClient. Ensure it is set up properly."


@pytest.mark.asyncio
async def test_credentials_fixture(sample_master_key: str) -> None:
    """
    Test the credentials fixture to ensure it is loaded correctly.

    """

    assert sample_master_key is not None, "Credentials fixture is None. Ensure it is set up properly."


@pytest.mark.asyncio
async def test_sample_document_index(sample_document_index: str) -> None:
    """
    Test the test group fixture to ensure it is loaded correctly.

    """

    assert sample_document_index is not None, "Test group fixture is None. Ensure it is set up properly."
