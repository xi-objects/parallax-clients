from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.problem_details import ProblemDetails
from ...models.published_record_response import PublishedRecordResponse
from typing import cast



def _get_kwargs(
    original_image_hash: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/records/{original_image_hash}".format(original_image_hash=quote(str(original_image_hash), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ProblemDetails | PublishedRecordResponse | None:
    if response.status_code == 200:
        response_200 = PublishedRecordResponse.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = ProblemDetails.from_dict(response.json())



        return response_400

    if response.status_code == 401:
        response_401 = ProblemDetails.from_dict(response.json())



        return response_401

    if response.status_code == 422:
        response_422 = ProblemDetails.from_dict(response.json())



        return response_422

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ProblemDetails | PublishedRecordResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    original_image_hash: str,
    *,
    client: AuthenticatedClient,

) -> Response[ProblemDetails | PublishedRecordResponse]:
    """ Recover one image's published record: the manifests it was registered with and the material to
    verify them.

    Args:
        original_image_hash (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | PublishedRecordResponse]
     """


    kwargs = _get_kwargs(
        original_image_hash=original_image_hash,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    original_image_hash: str,
    *,
    client: AuthenticatedClient,

) -> ProblemDetails | PublishedRecordResponse | None:
    """ Recover one image's published record: the manifests it was registered with and the material to
    verify them.

    Args:
        original_image_hash (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | PublishedRecordResponse
     """


    return sync_detailed(
        original_image_hash=original_image_hash,
client=client,

    ).parsed

async def asyncio_detailed(
    original_image_hash: str,
    *,
    client: AuthenticatedClient,

) -> Response[ProblemDetails | PublishedRecordResponse]:
    """ Recover one image's published record: the manifests it was registered with and the material to
    verify them.

    Args:
        original_image_hash (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | PublishedRecordResponse]
     """


    kwargs = _get_kwargs(
        original_image_hash=original_image_hash,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    original_image_hash: str,
    *,
    client: AuthenticatedClient,

) -> ProblemDetails | PublishedRecordResponse | None:
    """ Recover one image's published record: the manifests it was registered with and the material to
    verify them.

    Args:
        original_image_hash (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | PublishedRecordResponse
     """


    return (await asyncio_detailed(
        original_image_hash=original_image_hash,
client=client,

    )).parsed
