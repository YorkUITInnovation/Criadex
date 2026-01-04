import uuid

import pytest
from httpx import Response

from app.controllers.auth.check import AuthCheckResponse
from app.controllers.auth.create import AuthCreateResponse
from app.controllers.auth.delete import AuthDeleteResponse
from app.controllers.auth.reset import AuthResetResponse
from app.controllers.auth.keys import AuthKeysResponse
from .utils.test_client import CriaTestClient, assert_response_shape


@pytest.mark.asyncio
async def test_auth_positive(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    """
    Test the auth-related routes:
    - /auth/{api_key}/create
    - /auth/{api_key}/check
    - /auth/{api_key}/reset
    - /auth/{api_key}/delete

    TODO: Add edge cases (duplicates, non-existent keys) - AKA negative tests on these routes

    :param client: The test client
    :param master_headers: Master headers so that we can interact with the API
    :return: None

    """

    create_payload = {"master": True}
    test_key: str = "test-" + str(uuid.uuid4())
    test_key_2: str = test_key + "-2"

    # (1) Create the key
    json_response: Response = client.post(f"/auth/{test_key}/create", json=create_payload, headers=sample_master_headers)
    response: AuthCreateResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthCreateResponse)

    # Run checks on the response
    assert response.api_key == test_key
    assert response.master is True

    # (2) Check the key
    json_response: Response = client.get(f"/auth/{test_key}/check", headers=sample_master_headers)
    response: AuthCheckResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthCheckResponse)

    # Run checks on the response
    assert response.api_key == test_key
    assert response.authorized is True
    assert response.master is True

    # (3) Reset the key
    json_response: Response = client.patch(f"/auth/{test_key}/reset?new_key={test_key_2}", headers=sample_master_headers)
    response: AuthResetResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthResetResponse)

    # Run checks on the response
    assert response.new_key == test_key_2

    # Now delete it
    json_response: Response = client.delete(f"/auth/{test_key_2}/delete", headers=sample_master_headers)
    response: AuthDeleteResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthDeleteResponse)

    # Run checks on the response
    assert response.api_key == test_key_2


@pytest.mark.asyncio
async def test_auth_keys_endpoint_positive(
        client: CriaTestClient,
        sample_master_headers: dict
) -> None:
    """
    Test the /auth/keys/{api_key} endpoint for a positive scenario.
    """
    create_payload = {"master": False}
    test_key: str = "test-keys-endpoint-" + str(uuid.uuid4())

    # (1) Create the key
    json_response: Response = client.post(f"/auth/{test_key}/create", json=create_payload, headers=sample_master_headers)
    response: AuthCreateResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthCreateResponse)
    assert response.api_key == test_key
    assert response.master is False

    # (2) Check the key using the new /auth/keys/{api_key} endpoint
    json_response: Response = client.get(f"/auth/keys/{test_key}", headers=sample_master_headers)
    response: AuthKeysResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthKeysResponse)

    # Run checks on the response
    assert response.api_key == test_key
    assert response.authorized is True
    assert response.master is False

    # (3) Delete the key
    json_response: Response = client.delete(f"/auth/{test_key}/delete", headers=sample_master_headers)
    response: AuthDeleteResponse = assert_response_shape(json_response.json(), require_status=200, require_code="SUCCESS", custom_shape=AuthDeleteResponse)
    assert response.api_key == test_key
