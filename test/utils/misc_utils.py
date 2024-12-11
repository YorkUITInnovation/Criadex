import httpx
from httpx import Response

from app.controllers.group_auth.delete import GroupAuthDeleteResponse
from app.controllers.groups.about import GroupAboutResponse
from app.controllers.schemas import NOT_FOUND, GROUP_NOT_FOUND, SUCCESS
from utils.test_client import CriaTestClient, assert_response_shape


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
