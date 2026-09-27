"""The nine sequence route members, one call each, as a mixin `ParallaxClient` composes.

Mirrors the .NET client's `Sequences/Services` route members one for one: open and the frames
upload go through the raw multipart sender (`multipart[manifest[<kind>]]` parts, one octet-stream
file part per frame) since the generator cannot shape either body; every other route is the
generated request builder under `..generated.api.sequences`. Every call past open carries the
sequence's ticket, attached in exactly one place.
"""

# PC-113: the sequence conversation's nine route members, sync

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
from ..multipart import MultipartPart, build_sequence_frame_parts
from .encoding import SequenceFrameEncoder
from .models import EncodedFrame, OpenedSequence, SequenceHandle, SequenceOpenRequest
from .wire import TICKET_HEADER

#: The largest expected size the server accepts: an int32.
_MAX_EXPECTED_SIZE = 2**31 - 1

# PC-113: rework - the two hand-written routes' paths, declared once for both sync and async
OPEN_SEQUENCE_PATH = "/sequences"


def _sequence_frames_path(sequence_id: object) -> str:
    """The frames-upload path for a given sequence id, shared by both route mixins."""
    return f"/sequences/{sequence_id}/frames"


def _ticket_headers(handle: SequenceHandle) -> dict[str, str]:
    """The one place a ticket becomes an `httpx` header, for the two hand-written posts."""
    return {TICKET_HEADER: handle.ticket}


# PC-113: rework - built from _ticket_headers' value so exactly one line reads handle.ticket
def _ticket_kwargs(handle: SequenceHandle) -> dict[str, str]:
    """The same ticket, shaped as the keyword a generated sequence request function takes."""
    return {"x_sequence_ticket": _ticket_headers(handle)[TICKET_HEADER]}


def _open_sequence_parts(request: SequenceOpenRequest) -> list[MultipartPart]:
    """Build open's parts: `manifest[<kind>]` per manifest, then `expectedSize` when given."""
    parts: list[MultipartPart] = [
        (f"manifest[{manifest.kind}]", (None, manifest.data, manifest.form.content_type))
        for manifest in request.manifests
    ]
    if request.expected_size is not None:
        parts.append(("expectedSize", (None, str(request.expected_size).encode("ascii"), "text/plain")))
    return parts


def _refuse_non_positive_expected_size(expected_size: int) -> None:
    """Raise `ValueError` unless `expected_size` fits 1..2^31-1, the server's amend range."""
    if expected_size <= 0 or expected_size > _MAX_EXPECTED_SIZE:
        raise ValueError(f"expected_size must be between 1 and {_MAX_EXPECTED_SIZE}; was {expected_size}")


def _refuse_empty_frames(frames: Sequence[EncodedFrame]) -> None:
    """Raise `ValueError` when `frames` is empty; uploading needs at least one frame."""
    if not frames:
        raise ValueError("uploading a sequence's frames needs at least one frame")


# PC-113: what the routes mixin reads off its host client
class _SequenceRoutesHost(Protocol):
    """The host attributes `SequenceRoutes` reads: the generated API client, the codec, and httpx."""

    api: AuthenticatedClient
    frame_codec: object

    def _http(self) -> httpx.Client: ...


class SequenceRoutes:
    """Mixin adding the nine sequence route members to `ParallaxClient`.

    Reads `self.api`, `self.frame_codec` and `self._http()` from the host client; holds no state
    of its own.
    """

    # PC-113: opens a sequence; no ticket header, the HEAD frame decoded through the injected codec
    def open_sequence(self: _SequenceRoutesHost, request: SequenceOpenRequest) -> OpenedSequence:
        """Open a sequence (`POST /sequences`): manifest parts, then `expectedSize` when given.

        A 403 with slug `sequences-not-enabled` raises `problems.SequencesNotEnabled`.
        """
        parts = _open_sequence_parts(request)
        response = self._http().post(OPEN_SEQUENCE_PATH, files=parts)
        problems.raise_for_problem(response)
        opened = SequenceOpenResponse.from_dict(response.json())
        head_frame = base64.b64decode(opened.head_frame)
        head_frame_id = SequenceFrameEncoder(self.frame_codec).decode_head_frame_id(head_frame)
        return OpenedSequence(SequenceHandle(opened.sequence_id, opened.ticket), head_frame_id)

    # PC-113: uploads one batch of frames; refuses an empty list before any request
    def upload_sequence_frames(
        self: _SequenceRoutesHost, handle: SequenceHandle, frames: Sequence[EncodedFrame]
    ) -> SequenceFrameBatchResponse:
        """Upload one batch of encoded frames (`POST /sequences/{id}/frames`), under the ticket header."""
        _refuse_empty_frames(frames)
        parts = build_sequence_frame_parts(frames)
        response = self._http().post(
            _sequence_frames_path(handle.sequence_id), files=parts, headers=_ticket_headers(handle)
        )
        problems.raise_for_problem(response)
        return SequenceFrameBatchResponse.from_dict(response.json())

    # PC-113: removes one BODY member through the generated builder
    def remove_sequence_frame(self: _SequenceRoutesHost, handle: SequenceHandle, frame_id: int) -> None:
        """Remove one BODY frame (`DELETE /sequences/{id}/frames/{frameId}`), under the ticket header."""
        response = delete_sequences_sequence_id_frames_frame_id.sync_detailed(
            sequence_id=str(handle.sequence_id), frame_id=frame_id, client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)

    # PC-113: reads the sequence's current gaps
    def get_sequence_gaps(self: _SequenceRoutesHost, handle: SequenceHandle) -> SequenceGapsResponse:
        """Read the sequence's current gaps (`GET /sequences/{id}/gaps`), under the ticket header."""
        response = get_sequences_sequence_id_gaps.sync_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: reads the sequence's current verdict
    def get_sequence_progress(self: _SequenceRoutesHost, handle: SequenceHandle) -> SequenceVerdictResponse:
        """Read the sequence's progress (`GET /sequences/{id}/progress`), under the ticket header."""
        response = get_sequences_sequence_id_progress.sync_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: amends the advisory expected size; refuses out of 1..2^31-1 before any request
    def amend_sequence_expected_size(
        self: _SequenceRoutesHost, handle: SequenceHandle, expected_size: int
    ) -> None:
        """Amend the sequence's advisory expected size (`PUT /sequences/{id}/expected-size`)."""
        _refuse_non_positive_expected_size(expected_size)
        body = SequenceAmendExpectedSizeRequest(expected_size=expected_size)
        response = put_sequences_sequence_id_expected_size.sync_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, body=body, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)

    # PC-113: commits the sequence
    def commit_sequence(self: _SequenceRoutesHost, handle: SequenceHandle) -> SequenceCommitResponse:
        """Commit the sequence (`POST /sequences/{id}/commit`), under the ticket header."""
        response = post_sequences_sequence_id_commit.sync_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: reads the sequence's final results
    def get_sequence_results(self: _SequenceRoutesHost, handle: SequenceHandle) -> SequenceResultsResponse:
        """Read the sequence's final results (`GET /sequences/{id}/results`), under the ticket header."""
        response = get_sequences_sequence_id_results.sync_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    # PC-113: abandons the sequence outright
    def abandon_sequence(self: _SequenceRoutesHost, handle: SequenceHandle) -> SequenceAbandonResponse:
        """Abandon the sequence at once (`DELETE /sequences/{id}`), under the ticket header."""
        response = delete_sequences_sequence_id.sync_detailed(
            sequence_id=str(handle.sequence_id), client=self.api, **_ticket_kwargs(handle)
        )
        problems.raise_for_problem(response)
        return _parsed(response)
