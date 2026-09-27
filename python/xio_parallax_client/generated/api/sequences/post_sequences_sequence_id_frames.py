from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.post_sequences_sequence_id_frames_body import PostSequencesSequenceIdFramesBody
from ...models.problem_details import ProblemDetails
from ...models.sequence_frame_batch_response import SequenceFrameBatchResponse
from typing import cast



def _get_kwargs(
    sequence_id: str,
    *,
    body: PostSequencesSequenceIdFramesBody,
    x_sequence_ticket: str,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["X-Sequence-Ticket"] = x_sequence_ticket



    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/sequences/{sequence_id}/frames".format(sequence_id=quote(str(sequence_id), safe=""),),
    }

    _kwargs["files"] = body.to_multipart()

    headers["Content-Type"] = "multipart/form-data; boundary=+++"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ProblemDetails | SequenceFrameBatchResponse | None:
    if response.status_code == 201:
        response_201 = SequenceFrameBatchResponse.from_dict(response.json())



        return response_201

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

    if response.status_code == 413:
        response_413 = ProblemDetails.from_dict(response.json())



        return response_413

    if response.status_code == 422:
        response_422 = ProblemDetails.from_dict(response.json())



        return response_422

    if response.status_code == 500:
        response_500 = ProblemDetails.from_dict(response.json())



        return response_500

    if response.status_code == 503:
        response_503 = ProblemDetails.from_dict(response.json())



        return response_503

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ProblemDetails | SequenceFrameBatchResponse]:
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
    body: PostSequencesSequenceIdFramesBody,
    x_sequence_ticket: str,

) -> Response[ProblemDetails | SequenceFrameBatchResponse]:
    """ Admit one or more PX BODY frames to the sequence as one batch, all or nothing; a sealing batch's 201
    carries the verdict.

     The sequence's state is one of: open, sealed, committed, abandoned.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):
        body (PostSequencesSequenceIdFramesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SequenceFrameBatchResponse]
     """


    kwargs = _get_kwargs(
        sequence_id=sequence_id,
body=body,
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
    body: PostSequencesSequenceIdFramesBody,
    x_sequence_ticket: str,

) -> ProblemDetails | SequenceFrameBatchResponse | None:
    """ Admit one or more PX BODY frames to the sequence as one batch, all or nothing; a sealing batch's 201
    carries the verdict.

     The sequence's state is one of: open, sealed, committed, abandoned.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):
        body (PostSequencesSequenceIdFramesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SequenceFrameBatchResponse
     """


    return sync_detailed(
        sequence_id=sequence_id,
client=client,
body=body,
x_sequence_ticket=x_sequence_ticket,

    ).parsed

async def asyncio_detailed(
    sequence_id: str,
    *,
    client: AuthenticatedClient,
    body: PostSequencesSequenceIdFramesBody,
    x_sequence_ticket: str,

) -> Response[ProblemDetails | SequenceFrameBatchResponse]:
    """ Admit one or more PX BODY frames to the sequence as one batch, all or nothing; a sealing batch's 201
    carries the verdict.

     The sequence's state is one of: open, sealed, committed, abandoned.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):
        body (PostSequencesSequenceIdFramesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProblemDetails | SequenceFrameBatchResponse]
     """


    kwargs = _get_kwargs(
        sequence_id=sequence_id,
body=body,
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
    body: PostSequencesSequenceIdFramesBody,
    x_sequence_ticket: str,

) -> ProblemDetails | SequenceFrameBatchResponse | None:
    """ Admit one or more PX BODY frames to the sequence as one batch, all or nothing; a sealing batch's 201
    carries the verdict.

     The sequence's state is one of: open, sealed, committed, abandoned.

    Args:
        sequence_id (str):
        x_sequence_ticket (str):
        body (PostSequencesSequenceIdFramesBody):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProblemDetails | SequenceFrameBatchResponse
     """


    return (await asyncio_detailed(
        sequence_id=sequence_id,
client=client,
body=body,
x_sequence_ticket=x_sequence_ticket,

    )).parsed
