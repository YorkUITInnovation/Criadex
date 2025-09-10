from __future__ import annotations

import typing
from typing import Type, Optional

import httpx
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
        from app.controllers.schemas import APIResponse
        api_response = custom_shape(**response) if custom_shape else APIResponse(**response)

        if require_status:
            assert api_response.status == require_status, f"Status is {api_response.status}, expected {require_status}"

        if require_code:
            assert api_response.code == require_code, f"Code is {api_response.code}, expected {require_code}"

    except Exception as e:
        raise AssertionError(f"Response shape is incorrect (does not match APIResponse): {e}")

    return api_response