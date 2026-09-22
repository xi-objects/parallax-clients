from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.post_lookup_slots_lookup_slot_id_queries_body import PostLookupSlotsLookupSlotIdQueriesBody
from ...models.problem_details import ProblemDetails
from ...models.slot_upload_response import SlotUploadResponse
from typing import cast



def _get_kwargs(
    lookup_slot_id: str,
    *,
    body: PostLookupSlotsLookupSlotIdQueriesBody,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/lookup/slots/{lookup_slot_id}/queries".format(lookup_slot_id=quote(str(lookup_slot_id), safe=""),),
    }

    _kwargs["files"] = body.to_multipart()

    headers["Content-Type"] = "multipart/form-data; boundary=+++"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ProblemDetails | SlotUploadResponse | None:
    if response.status_code == 200:
        response_200 = SlotUploadResponse.from_dict(response.json())



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

    if response.status_code == 409:
        response_409 = ProblemDetails.from_dict(response.json())



        return response_409

    if response.status_code == 413:
        response_413 = ProblemDetails.from_dict(response.json())



        return response_413

    if response.status_code == 429:
        response_429 = ProblemDetails.from_dict(response.json())



        return response_429

    if response.status_code == 503:
        response_503 = ProblemDetails.from_dict(response.json())



        return response_503

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ProblemDetails | SlotUploadResponse]:
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
    body: PostLookupSlotsLookupSlotIdQueriesBody,

) -> Response[ProblemDetails | SlotUploadResponse]:
    """ Upload query images into a look-up slot; no verdict is reached until commit.

    Args:
        lookup_slot_id (str):
        body (PostLookupSlotsLookupSlotIdQueriesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SlotUploadResponse]
     """


    kwargs = _get_kwargs(
        lookup_slot_id=lookup_slot_id,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,
    body: PostLookupSlotsLookupSlotIdQueriesBody,

) -> ProblemDetails | SlotUploadResponse | None:
    """ Upload query images into a look-up slot; no verdict is reached until commit.

    Args:
        lookup_slot_id (str):
        body (PostLookupSlotsLookupSlotIdQueriesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SlotUploadResponse
     """


    return sync_detailed(
        lookup_slot_id=lookup_slot_id,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,
    body: PostLookupSlotsLookupSlotIdQueriesBody,

) -> Response[ProblemDetails | SlotUploadResponse]:
    """ Upload query images into a look-up slot; no verdict is reached until commit.

    Args:
        lookup_slot_id (str):
        body (PostLookupSlotsLookupSlotIdQueriesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SlotUploadResponse]
     """


    kwargs = _get_kwargs(
        lookup_slot_id=lookup_slot_id,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    lookup_slot_id: str,
    *,
    client: AuthenticatedClient,
    body: PostLookupSlotsLookupSlotIdQueriesBody,

) -> ProblemDetails | SlotUploadResponse | None:
    """ Upload query images into a look-up slot; no verdict is reached until commit.

    Args:
        lookup_slot_id (str):
        body (PostLookupSlotsLookupSlotIdQueriesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SlotUploadResponse
     """


    return (await asyncio_detailed(
        lookup_slot_id=lookup_slot_id,
client=client,
body=body,

    )).parsed
