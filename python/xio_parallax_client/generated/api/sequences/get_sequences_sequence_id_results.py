from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.problem_details import ProblemDetails
from ...models.sequence_results_response import SequenceResultsResponse
from typing import cast



def _get_kwargs(
    sequence_id: str,
    *,
    x_sequence_ticket: str,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Sequence-Ticket"] = x_sequence_ticket



    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/sequences/{sequence_id}/results".format(sequence_id=quote(str(sequence_id), safe=""),),
    }


    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ProblemDetails | SequenceResultsResponse | None:
    if response.status_code == 200:
        response_200 = SequenceResultsResponse.from_dict(response.json())



        return response_200

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ProblemDetails | SequenceResultsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    sequence_id: str,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> Response[ProblemDetails | SequenceResultsResponse]:
    """ Read a committed sequence's own record.

     The outcome is one of: registered, alreadyRegistered.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SequenceResultsResponse]
     """


    kwargs = _get_kwargs(
        sequence_id=sequence_id,
x_sequence_ticket=x_sequence_ticket,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    sequence_id: str,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> ProblemDetails | SequenceResultsResponse | None:
    """ Read a committed sequence's own record.

     The outcome is one of: registered, alreadyRegistered.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SequenceResultsResponse
     """


    return sync_detailed(
        sequence_id=sequence_id,
client=client,
x_sequence_ticket=x_sequence_ticket,

    ).parsed

async def asyncio_detailed(
    sequence_id: str,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> Response[ProblemDetails | SequenceResultsResponse]:
    """ Read a committed sequence's own record.

     The outcome is one of: registered, alreadyRegistered.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SequenceResultsResponse]
     """


    kwargs = _get_kwargs(
        sequence_id=sequence_id,
x_sequence_ticket=x_sequence_ticket,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    sequence_id: str,
    *,
    client: AuthenticatedClient,
    x_sequence_ticket: str,

) -> ProblemDetails | SequenceResultsResponse | None:
    """ Read a committed sequence's own record.

     The outcome is one of: registered, alreadyRegistered.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SequenceResultsResponse
     """


    return (await asyncio_detailed(
        sequence_id=sequence_id,
client=client,
x_sequence_ticket=x_sequence_ticket,

    )).parsed
