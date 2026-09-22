from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.problem_details import ProblemDetails
from typing import cast
from uuid import UUID



def _get_kwargs(
    account_id: UUID,
    token_id: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/admin/accounts/{account_id}/tokens/{token_id}/revoke".format(account_id=quote(str(account_id), safe=""),token_id=quote(str(token_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | ProblemDetails | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | ProblemDetails]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    account_id: UUID,
    token_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[Any | ProblemDetails]:
    """ Revoke one of an account's tokens; a repeated call changes nothing.

    Args:
        account_id (UUID):
        token_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ProblemDetails]
     """


    kwargs = _get_kwargs(
        account_id=account_id,
token_id=token_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    account_id: UUID,
    token_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Any | ProblemDetails | None:
    """ Revoke one of an account's tokens; a repeated call changes nothing.

    Args:
        account_id (UUID):
        token_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ProblemDetails
     """


    return sync_detailed(
        account_id=account_id,
token_id=token_id,
client=client,

    ).parsed

async def asyncio_detailed(
    account_id: UUID,
    token_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Response[Any | ProblemDetails]:
    """ Revoke one of an account's tokens; a repeated call changes nothing.

    Args:
        account_id (UUID):
        token_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ProblemDetails]
     """


    kwargs = _get_kwargs(
        account_id=account_id,
token_id=token_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    account_id: UUID,
    token_id: UUID,
    *,
    client: AuthenticatedClient,

) -> Any | ProblemDetails | None:
    """ Revoke one of an account's tokens; a repeated call changes nothing.

    Args:
        account_id (UUID):
        token_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ProblemDetails
     """


    return (await asyncio_detailed(
        account_id=account_id,
token_id=token_id,
client=client,

    )).parsed
