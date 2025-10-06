import httpx
from httpx import Response

from app.controllers.group_auth.delete import GroupAuthDeleteResponse
from app.controllers.groups.about import GroupAboutResponse
from app.controllers.groups.delete import GroupDeleteResponse
from criadex.schemas import NOT_FOUND, GROUP_NOT_FOUND, SUCCESS, GroupExistsResponse
from test.utils.test_client import CriaTestClient, assert_response_shape
from criadex.index.schemas import IndexResponse


async def assert_exists_index(
        client: CriaTestClient,
        master_headers: dict,
        group_name: str
) -> None:
    """
    Check if the test index exists

    :param client: The test client
    :param master_headers: The master
    :param group_name: The test index
    :return: Whether the index exists

    """

    response: GroupAboutResponse = client.get_json(f"/groups/{group_name}/about", headers=master_headers, apply_shape=GroupAboutResponse)

    assert response.status != 404, "The test index does not exist"
    assert response.status == 200, "Error in checking if the test index exists!"


async def reset_group_auth(
        client: CriaTestClient,
        master_headers: dict,
        group_name: str,
        api_key: str
) -> None:
    """
    Reset the auth of a key on a group

    :param client: The client
    :param master_headers: Headers to apply to check
    :param group_name: The name of the group
    :param api_key: The key to delete
    :return: N/A

    """

    response: Response = client.delete(
        f"/group_auth/{group_name}/delete?api_key={api_key}",
        headers=master_headers
    )

    response: GroupAuthDeleteResponse = assert_response_shape(response.json(), require_status=None, require_code=None, custom_shape=GroupAuthDeleteResponse)
    assert response.code in ["SUCCESS", "NOT_FOUND"]


async def assert_does_not_exist_index(client: CriaTestClient, headers: dict, index_name: str) -> None:
    """
    Asserts that the given index does not exist. If it does, it deletes it.

    :param client: The test client
    :param headers: The headers
    :param index_name: The index name
    :return: None
    """
    print(f"DEBUG: Checking existence of index for cleanup: {index_name}")
    response = client.get(
        f"/groups/{index_name}/exists",
        headers=headers
    )

    response_data: GroupExistsResponse = assert_response_shape(response.json(), custom_shape=GroupExistsResponse)
    print(f"DEBUG: Index {index_name} exists for cleanup: {response_data.exists}, Status: {response_data.status}, Code: {response_data.code}")

    if response_data.exists:
        print(f"DEBUG: Deleting index for cleanup: {index_name}")
        response = client.delete(
            f"/groups/{index_name}/delete",
            headers=headers
        )
        delete_response_data: GroupDeleteResponse = assert_response_shape(response.json(), custom_shape=GroupDeleteResponse)
        print(f"DEBUG: Delete index {index_name} Status: {delete_response_data.status}, Code: {delete_response_data.code}")
        assert delete_response_data.status == 200 and delete_response_data.code == "SUCCESS", f"Failed to delete index {index_name}"

    assert response_data.status == 200 and response_data.code == "SUCCESS", f"Failed to check if index {index_name} exists"

    print(f"DEBUG: Finished checking/deleting index for cleanup: {index_name}")
    return None