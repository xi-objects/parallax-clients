from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.account_response import AccountResponse
from ...models.problem_details import ProblemDetails
from ...models.update_account_request import UpdateAccountRequest
from typing import cast
from uuid import UUID



def _get_kwargs(
    account_id: UUID,
    *,
    body: UpdateAccountRequest,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/admin/accounts/{account_id}".format(account_id=quote(str(account_id), safe=""),),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> AccountResponse | ProblemDetails | None:
    if response.status_code == 200:
        response_200 = AccountResponse.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = ProblemDetails.from_dict(response.json())



        return response_400

    if response.status_code == 401:
        response_401 = ProblemDetails.from_dict(response.json())



        return response_401

    if response.status_code == 404:
        response_404 = ProblemDetails.from_dict(response.json())



        return response_404

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[AccountResponse | ProblemDetails]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    account_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateAccountRequest,

) -> Response[AccountResponse | ProblemDetails]:
    """ Replace an existing account's grants and limit values.

    Args:
        account_id (UUID):
        body (UpdateAccountRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AccountResponse | ProblemDetails]
     """


    kwargs = _get_kwargs(
        account_id=account_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    account_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateAccountRequest,

) -> AccountResponse | ProblemDetails | None:
    """ Replace an existing account's grants and limit values.

    Args:
        account_id (UUID):
        body (UpdateAccountRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AccountResponse | ProblemDetails
     """


    return sync_detailed(
        account_id=account_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    account_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateAccountRequest,

) -> Response[AccountResponse | ProblemDetails]:
    """ Replace an existing account's grants and limit values.

    Args:
        account_id (UUID):
        body (UpdateAccountRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AccountResponse | ProblemDetails]
     """


    kwargs = _get_kwargs(
        account_id=account_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    account_id: UUID,
    *,
    client: AuthenticatedClient,
    body: UpdateAccountRequest,

) -> AccountResponse | ProblemDetails | None:
    """ Replace an existing account's grants and limit values.

    Args:
        account_id (UUID):
        body (UpdateAccountRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AccountResponse | ProblemDetails
     """


    return (await asyncio_detailed(
        account_id=account_id,
client=client,
body=body,

    )).parsed
