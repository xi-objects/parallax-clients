"""The async mirror of `sequences.routes`: the nine sequence route members, one call each.

See `routes.py` for the shared shape; this module differs only by `async def` / `await` and the
generated functions' `asyncio_detailed` entry points.
"""

# PC-113: the sequence conversation's nine route members, async

from __future__ import annotations

import base64
from collections.abc import Sequence
from typing import Protocol

import httpx

from .. import problems
from .._calls import _parsed
from ..generated.api.sequences import (
    delete_sequences_sequence_id,
    delete_sequences_sequence_id_frames_frame_id,
    get_sequences_sequence_id_gaps,
    get_sequences_sequence_id_progress,
    get_sequences_sequence_id_results,
    post_sequences_sequence_id_commit,
    put_sequences_sequence_id_expected_size,
)
from ..generated.client import AuthenticatedClient
from ..generated.models import (
    SequenceAbandonResponse,
    SequenceAmendExpectedSizeRequest,
    SequenceCommitResponse,
    SequenceFrameBatchResponse,
    SequenceGapsResponse,
    SequenceOpenResponse,
    SequenceResultsResponse,
    SequenceVerdictResponse,
)
from ..multipart import build_sequence_frame_parts
from .encoding import SequenceFrameEncoder
from .models import EncodedFrame, OpenedSequence, SequenceHandle, SequenceOpenRequest
from .routes import (
    _open_sequence_parts,
    _refuse_empty_frames,
    _refuse_non_positive_expected_size,
    _ticket_headers,
    _ticket_kwargs,
)


# PC-113: what the async routes mixin reads off its host client
class _AsyncSequenceRoutesHost(Protocol):
    """The host attributes `AsyncSequenceRoutes` reads: the generated API client, the codec, and httpx."""

    api: AuthenticatedClient
    frame_codec: object

    def _http(self) -> httpx.AsyncClient: ...


class AsyncSequenceRoutes:
    """Async mirror of `SequenceRoutes`; see its docstring."""

    # PC-113: opens a sequence; no ticket header, the HEAD frame decoded through the injected codec
    async def open_sequence(self: _AsyncSequenceRoutesHost, request: SequenceOpenRequest) -> OpenedSequence:
        """Async mirror of `SequenceRoutes.open_sequence`."""
        parts = _open_sequence_parts(request)
        response = await self._http().post("/sequences", files=parts)
        problems.raise_for_problem(response)
        opened = SequenceOpenResponse.from_dict(response.json())
        head_frame = base64.b64decode(opened.head_frame)
        head_frame_id = SequenceFrameEncoder(self.frame_codec).decode_head_frame_id(head_frame)
        return OpenedSequence(SequenceHandle(opened.sequence_id, opened.ticket), head_frame_id)

    # PC-113: uploads one batch of frames; refuses an empty list before any request
    async def upload_sequence_frames(
        self: _AsyncSequenceRoutesHost, handle: SequenceHandle, frames: Sequence[EncodedFrame]
    ) -> SequenceFrameBatchResponse:
        """Async mirror of `SequenceRoutes.upload_sequence_frames`."""
        _refuse_empty_frames(frames)
        parts = build_sequence_frame_parts(frames)
        response = await self._http().post(
            f"/sequences/{handle.sequence_id}/frames", files=parts, headers=_ticket_headers(handle)
        )
        problems.raise_for_problem(response)
        return SequenceFrameBatchResponse.from_dict(response.json())

    # PC-113: removes one BODY member through the generated builder
    async def remove_sequence_frame(self: _AsyncSequenceRoutesHost, handle: SequenceHandle, frame_id: int) -> None:
        """Async mirror of `SequenceRoutes.remove_sequence_frame`."""
        response = await delete_sequences_sequence_id_frames_frame_id.asyncio_detailed(
            sequence_id=str(handle.sequence_id), frame_id=frame_id, client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)

    # PC-113: reads the sequence's current gaps
    async def get_sequence_gaps(self: _AsyncSequenceRoutesHost, handle: SequenceHandle) -> SequenceGapsResponse:
        """Async mirror of `SequenceRoutes.get_sequence_gaps`."""
        response = await get_sequences_sequence_id_gaps.asyncio_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: reads the sequence's current verdict
    async def get_sequence_progress(self: _AsyncSequenceRoutesHost, handle: SequenceHandle) -> SequenceVerdictResponse:
        """Async mirror of `SequenceRoutes.get_sequence_progress`."""
        response = await get_sequences_sequence_id_progress.asyncio_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: amends the advisory expected size; refuses out of 1..2^31-1 before any request
    async def amend_sequence_expected_size(
        self: _AsyncSequenceRoutesHost, handle: SequenceHandle, expected_size: int
    ) -> None:
        """Async mirror of `SequenceRoutes.amend_sequence_expected_size`."""
        _refuse_non_positive_expected_size(expected_size)
        body = SequenceAmendExpectedSizeRequest(expected_size=expected_size)
        response = await put_sequences_sequence_id_expected_size.asyncio_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, body=body, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)

    # PC-113: commits the sequence
    async def commit_sequence(self: _AsyncSequenceRoutesHost, handle: SequenceHandle) -> SequenceCommitResponse:
        """Async mirror of `SequenceRoutes.commit_sequence`."""
        response = await post_sequences_sequence_id_commit.asyncio_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: reads the sequence's final results
    async def get_sequence_results(self: _AsyncSequenceRoutesHost, handle: SequenceHandle) -> SequenceResultsResponse:
        """Async mirror of `SequenceRoutes.get_sequence_results`."""
        response = await get_sequences_sequence_id_results.asyncio_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: abandons the sequence outright
    async def abandon_sequence(self: _AsyncSequenceRoutesHost, handle: SequenceHandle) -> SequenceAbandonResponse:
        """Async mirror of `SequenceRoutes.abandon_sequence`."""
        response = await delete_sequences_sequence_id.asyncio_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)
