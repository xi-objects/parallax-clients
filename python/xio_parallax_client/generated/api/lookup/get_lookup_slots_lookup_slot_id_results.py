from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.lookup_results_response import LookupResultsResponse
from ...models.problem_details import ProblemDetails
from typing import cast



def _get_kwargs(
    lookup_slot_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/lookup/slots/{lookup_slot_id}/results".format(lookup_slot_id=quote(str(lookup_slot_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> LookupResultsResponse | ProblemDetails | None:
    if response.status_code == 200:
        response_200 = LookupResultsResponse.from_dict(response.json())



        return response_200

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[LookupResultsResponse | ProblemDetails]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[LookupResultsResponse | ProblemDetails]:
    """ Read every query's verdict, until the slot's TTL takes it.

     Every entry's state is one of: held, registered, answered, failed, errata, retry. "retry" says the
    engine could not answer that entry yet: nothing was registered, answered or charged for it, and
    because a commit is terminal this service never re-sends it - the client sends that image again, in
    a new slot or through the single route.

    Args:
        lookup_slot_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[LookupResultsResponse | ProblemDetails]
     """


    kwargs = _get_kwargs(
        lookup_slot_id=lookup_slot_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,

) -> LookupResultsResponse | ProblemDetails | None:
    """ Read every query's verdict, until the slot's TTL takes it.

     Every entry's state is one of: held, registered, answered, failed, errata, retry. "retry" says the
    engine could not answer that entry yet: nothing was registered, answered or charged for it, and
    because a commit is terminal this service never re-sends it - the client sends that image again, in
    a new slot or through the single route.

    Args:
        lookup_slot_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        LookupResultsResponse | ProblemDetails
     """


    return sync_detailed(
        lookup_slot_id=lookup_slot_id,
client=client,

    ).parsed

async def asyncio_detailed(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[LookupResultsResponse | ProblemDetails]:
    """ Read every query's verdict, until the slot's TTL takes it.

     Every entry's state is one of: held, registered, answered, failed, errata, retry. "retry" says the
    engine could not answer that entry yet: nothing was registered, answered or charged for it, and
    because a commit is terminal this service never re-sends it - the client sends that image again, in
    a new slot or through the single route.

    Args:
        lookup_slot_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[LookupResultsResponse | ProblemDetails]
     """


    kwargs = _get_kwargs(
        lookup_slot_id=lookup_slot_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,

) -> LookupResultsResponse | ProblemDetails | None:
    """ Read every query's verdict, until the slot's TTL takes it.

     Every entry's state is one of: held, registered, answered, failed, errata, retry. "retry" says the
    engine could not answer that entry yet: nothing was registered, answered or charged for it, and
    because a commit is terminal this service never re-sends it - the client sends that image again, in
    a new slot or through the single route.

    Args:
        lookup_slot_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        LookupResultsResponse | ProblemDetails
     """


    return (await asyncio_detailed(
        lookup_slot_id=lookup_slot_id,
client=client,

    )).parsed
