from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.problem_details import ProblemDetails
from ...models.put_slots_slot_id_entries_image_hash_manifests_body import PutSlotsSlotIdEntriesImageHashManifestsBody
from ...models.slot_manifest_entry_response import SlotManifestEntryResponse
from typing import cast



def _get_kwargs(
    slot_id: str,
    image_hash: str,
    *,
    body: PutSlotsSlotIdEntriesImageHashManifestsBody,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/slots/{slot_id}/entries/{image_hash}/manifests".format(slot_id=quote(str(slot_id), safe=""),image_hash=quote(str(image_hash), safe=""),),
    }

    _kwargs["files"] = body.to_multipart()

    headers["Content-Type"] = "multipart/form-data; boundary=+++"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ProblemDetails | SlotManifestEntryResponse | None:
    if response.status_code == 200:
        response_200 = SlotManifestEntryResponse.from_dict(response.json())



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

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ProblemDetails | SlotManifestEntryResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    slot_id: str,
    image_hash: str,
    *,
    client: AuthenticatedClient,
    body: PutSlotsSlotIdEntriesImageHashManifestsBody,

) -> Response[ProblemDetails | SlotManifestEntryResponse]:
    """ Replace, as one whole list, the manifests one held entry carries.

    Args:
        slot_id (str):
        image_hash (str):
        body (PutSlotsSlotIdEntriesImageHashManifestsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SlotManifestEntryResponse]
     """


    kwargs = _get_kwargs(
        slot_id=slot_id,
image_hash=image_hash,
body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    slot_id: str,
    image_hash: str,
    *,
    client: AuthenticatedClient,
    body: PutSlotsSlotIdEntriesImageHashManifestsBody,

) -> ProblemDetails | SlotManifestEntryResponse | None:
    """ Replace, as one whole list, the manifests one held entry carries.

    Args:
        slot_id (str):
        image_hash (str):
        body (PutSlotsSlotIdEntriesImageHashManifestsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SlotManifestEntryResponse
     """


    return sync_detailed(
        slot_id=slot_id,
image_hash=image_hash,
client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    slot_id: str,
    image_hash: str,
    *,
    client: AuthenticatedClient,
    body: PutSlotsSlotIdEntriesImageHashManifestsBody,

) -> Response[ProblemDetails | SlotManifestEntryResponse]:
    """ Replace, as one whole list, the manifests one held entry carries.

    Args:
        slot_id (str):
        image_hash (str):
        body (PutSlotsSlotIdEntriesImageHashManifestsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SlotManifestEntryResponse]
     """


    kwargs = _get_kwargs(
        slot_id=slot_id,
image_hash=image_hash,
body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    slot_id: str,
    image_hash: str,
    *,
    client: AuthenticatedClient,
    body: PutSlotsSlotIdEntriesImageHashManifestsBody,

) -> ProblemDetails | SlotManifestEntryResponse | None:
    """ Replace, as one whole list, the manifests one held entry carries.

    Args:
        slot_id (str):
        image_hash (str):
        body (PutSlotsSlotIdEntriesImageHashManifestsBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SlotManifestEntryResponse
     """


    return (await asyncio_detailed(
        slot_id=slot_id,
image_hash=image_hash,
client=client,
body=body,

    )).parsed
