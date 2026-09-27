"""Sequence conversation models: the frozen dataclasses `register_sequence` and its routes share.

Mirrors `Xio.Parallax.Client.Sequences.Models` one for one. Nothing here does I/O; every refusal
is a `ValueError` raised before any request, naming every offending field together where more than
one field is checked at once.
"""

# PC-111: sequence conversation models

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from ..frames.protocol import PxFrameType
from ..multipart import ManifestPart

if TYPE_CHECKING:
    from ..generated.models.sequence_commit_response import SequenceCommitResponse
    from ..generated.models.sequence_results_response import SequenceResultsResponse
    from ..generated.models.sequence_verdict_response import SequenceVerdictResponse


def _refuse_all(errors: Sequence[str]) -> None:
    """Raise `ValueError` joining every message in `errors`, or do nothing when it is empty."""
    if errors:
        raise ValueError("; ".join(errors))


@dataclass(frozen=True, slots=True, repr=False)
class SequenceHandle:
    """A sequence's id and the ticket every route past open sends as `X-Sequence-Ticket`.

    `repr` prints `sequence_id` but redacts `ticket`, the same way `ParallaxClientOptions` hides
    its secrets.
    """

    sequence_id: UUID
    ticket: str = field(repr=False)

    def __repr__(self) -> str:
        return f"SequenceHandle(sequence_id={self.sequence_id!r}, ticket=[redacted])"


@dataclass(frozen=True, slots=True)
class OpenedSequence:
    """A sequence just opened or resumed: its handle, and the id of its HEAD frame."""

    handle: SequenceHandle
    head_frame_id: int


@dataclass(frozen=True, slots=True)
class SequenceOpenRequest:
    """The manifests and optional expected size a sequence opens with.

    Both fields are required positionally, with no default; `expected_size`, when given, is above
    zero.
    """

    manifests: Sequence[ManifestPart]
    expected_size: int | None

    def __post_init__(self) -> None:
        if self.expected_size is not None and self.expected_size <= 0:
            raise ValueError(f"expected_size must be above zero when given; was {self.expected_size}")


@dataclass(frozen=True, slots=True)
class SequenceBatching:
    """The operator-configured caps a batched sequence frame upload must respect; no default.

    Neither cap is declared by the OpenAPI document, so the caller states them.
    """

    max_request_bytes: int
    max_frames_per_request: int

    def __post_init__(self) -> None:
        errors: list[str] = []
        if self.max_request_bytes <= 0:
            errors.append(f"max_request_bytes must be above zero; was {self.max_request_bytes}")
        if self.max_frames_per_request <= 0:
            errors.append(f"max_frames_per_request must be above zero; was {self.max_frames_per_request}")
        _refuse_all(errors)


@dataclass(frozen=True, slots=True)
class SequenceRegisterOptions:
    """Options for `register_sequence`: how it opens or resumes, batches uploads, and retries a commit.

    `poll_interval`, `commit_attempts` and `batching` are required, with no default; every bad
    field is named together in one `ValueError`. Exactly one of `open`/`existing` is checked once
    the conversation starts, not here.
    """

    poll_interval: float
    commit_attempts: int
    batching: SequenceBatching
    open: SequenceOpenRequest | None = None
    existing: OpenedSequence | None = None

    def __post_init__(self) -> None:
        errors: list[str] = []
        if self.poll_interval <= 0:
            errors.append(f"poll_interval must be above zero; was {self.poll_interval}")
        if self.commit_attempts < 1:
            errors.append(f"commit_attempts must be at least one; was {self.commit_attempts}")
        if self.batching is None:
            errors.append("batching is required; there is no default")
        _refuse_all(errors)


@dataclass(frozen=True, slots=True)
class SequenceRegisterResult:
    """The outcome of `register_sequence`: the sequence it ran in, its verdict, commit and results."""

    sequence: OpenedSequence
    verdict: SequenceVerdictResponse
    commit: SequenceCommitResponse
    results: SequenceResultsResponse


@dataclass(frozen=True, slots=True)
class EncodedFrame:
    """One sequence frame already encoded for the wire: its id, type, bytes and frame hash."""

    frame_id: int
    frame_type: PxFrameType
    data: bytes
    frame_hash: bytes


#: The Python form of `IProgress<SequenceVerdictResponse>`, as `ProgressCallback` is for slots.
VerdictCallback = Callable[["SequenceVerdictResponse"], None]
