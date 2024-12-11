import pytest
from httpx import Response

from app.controllers.group_auth.check import GroupAuthCheckResponse
from app.controllers.group_auth.create import GroupAuthCreateResponse
from app.controllers.group_auth.delete import GroupAuthDeleteResponse
from app.controllers.group_auth.list import GroupAuthListResponse
from utils.misc_utils import assert_exists_index, reset_group_auth
from utils.test_client import CriaTestClient, sample_master_headers, sample_document_index, sample_question_index, client, sample_master_key, assert_response_shape, sample_non_master_key


@pytest.mark.asyncio
async def test_group_auth_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_document_index: str,
        sample_question_index: str,
        sample_non_master_key: str
) -> None:
    """
    Test the group auth-related routes:
    - /group_auth/{group}/create
    - /group_auth/{group}/check
    - /group_auth/{group}/delete
    - /group_auth/list

    """

    # Confirm the index exists before performing test operations
    await assert_exists_index(client, sample_master_headers, sample_document_index)

    # Reset group auth to ensure a clean slate for the test
    await reset_group_auth(client, sample_master_headers, sample_document_index, api_key=sample_non_master_key)

    # (1) Create the group auth for the test credentials
    response: Response = client.post(f"/group_auth/{sample_document_index}/create?api_key={sample_non_master_key}", headers=sample_master_headers)
    response_data: GroupAuthCreateResponse = assert_response_shape(response.json(), custom_shape=GroupAuthCreateResponse)

    # Run checks on the response
    print(response_data)
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to authenticate the test key on the index"

    # (2) Test if the group is in the list of auth
    response: Response = client.get(f"/group_auth/list?api_key={sample_non_master_key}", headers=sample_master_headers)
    response_data: GroupAuthListResponse = assert_response_shape(response.json(), custom_shape=GroupAuthListResponse)

    # Run checks on the response (i.e. that the group is in the list means authentication worked)
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to identify the test index in the test key's list of authorized groups"
    assert any([group.name == sample_document_index for group in response_data.groups]), "The API key was unsuccessfully authenticated on the index group"

    # (3) Check if the user is authorized (2nd way)
    response: Response = client.get(f"/group_auth/{sample_document_index}/check?api_key={sample_non_master_key}", headers=sample_master_headers)
    response_data: GroupAuthCheckResponse = assert_response_shape(response.json(), custom_shape=GroupAuthCheckResponse)

    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to check if the API key was authorized on the index group"
    assert response_data.authorized is True, "The API key was not authorized on the index group"

    # (4) Delete the group auth
    response: Response = client.delete(f"/group_auth/{sample_document_index}/delete?api_key={sample_non_master_key}", headers=sample_master_headers)
    response_data: GroupAuthDeleteResponse = assert_response_shape(response.json(), custom_shape=GroupAuthDeleteResponse)

    # Run checks on the response
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to delete the authorization on the index group"

    # (5) Re-check if they are authorized (should be false)
    response: Response = client.get(f"/group_auth/{sample_document_index}/check?api_key={sample_non_master_key}", headers=sample_master_headers)
    response_data: GroupAuthCheckResponse = assert_response_shape(response.json(), custom_shape=GroupAuthCheckResponse)

    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to check if the API key was authorized on the index group"
    assert response_data.authorized is False, "The API key was still authorized on the index group after deletion!"
