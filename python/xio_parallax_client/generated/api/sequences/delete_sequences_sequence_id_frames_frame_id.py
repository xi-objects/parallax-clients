from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.problem_details import ProblemDetails
from typing import cast



def _get_kwargs(
    sequence_id: str,
    frame_id: int,
    *,
    x_sequence_ticket: str,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Sequence-Ticket"] = x_sequence_ticket



    

    

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/sequences/{sequence_id}/frames/{frame_id}".format(sequence_id=quote(str(sequence_id), safe=""),frame_id=quote(str(frame_id), safe=""),),
    }


    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | ProblemDetails | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = ProblemDetails.from_dict(response.json())



        return response_400

    if response.status_code == 401:
        response_401 = ProblemDetails.from_dict(response.json())



        return response_401

    if response.status_code == 403:
        response_403 = ProblemDetails.from_dict(response.json())



        return response_403

    if response.status_code == 404:
        response_404 = ProblemDetails.from_dict(response.json())



        return response_404

    if response.status_code == 409:
        response_409 = ProblemDetails.from_dict(response.json())



        return response_409

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
    sequence_id: str,
    frame_id: int,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> Response[Any | ProblemDetails]:
    """ Remove one BODY member from the sequence.

    Args:
        sequence_id (str):
        frame_id (int):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ProblemDetails]
     """


    kwargs = _get_kwargs(
        sequence_id=sequence_id,
frame_id=frame_id,
x_sequence_ticket=x_sequence_ticket,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    sequence_id: str,
    frame_id: int,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> Any | ProblemDetails | None:
    """ Remove one BODY member from the sequence.

    Args:
        sequence_id (str):
        frame_id (int):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ProblemDetails
     """


    return sync_detailed(
        sequence_id=sequence_id,
frame_id=frame_id,
client=client,
x_sequence_ticket=x_sequence_ticket,

    ).parsed

async def asyncio_detailed(
    sequence_id: str,
    frame_id: int,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> Response[Any | ProblemDetails]:
    """ Remove one BODY member from the sequence.

    Args:
        sequence_id (str):
        frame_id (int):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ProblemDetails]
     """


    kwargs = _get_kwargs(
        sequence_id=sequence_id,
frame_id=frame_id,
x_sequence_ticket=x_sequence_ticket,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    sequence_id: str,
    frame_id: int,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> Any | ProblemDetails | None:
    """ Remove one BODY member from the sequence.

    Args:
        sequence_id (str):
        frame_id (int):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ProblemDetails
     """


    return (await asyncio_detailed(
        sequence_id=sequence_id,
frame_id=frame_id,
client=client,
x_sequence_ticket=x_sequence_ticket,

    )).parsed
