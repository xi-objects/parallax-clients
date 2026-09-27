"""PC-111: sequence conversation models, every refusal, and the handle's redacting repr."""

from __future__ import annotations

from uuid import UUID

import pytest
from xio_parallax_client.frames.protocol import PxFrameType
from xio_parallax_client.generated.models.sequence_commit_frame_response import SequenceCommitFrameResponse
from xio_parallax_client.generated.models.sequence_commit_response import SequenceCommitResponse
from xio_parallax_client.generated.models.sequence_verdict_response import SequenceVerdictResponse
from xio_parallax_client.sequences.errors import SequenceCommitError, SequenceVerdictError
from xio_parallax_client.sequences.models import (
    EncodedFrame,
    OpenedSequence,
    SequenceBatching,
    SequenceHandle,
    SequenceOpenRequest,
    SequenceRegisterOptions,
)

_SEQUENCE_ID = UUID(int=1)


def _verdict(gaps: list | None = None, errata: list | None = None, connected: bool = False) -> SequenceVerdictResponse:
    return SequenceVerdictResponse(
        state="sealed",
        frames_received=3,
        expected_size=None,
        reach=3,
        gaps=gaps or [],
        errata=errata or [],
        connected=connected,
    )


def _commit(frames: list) -> SequenceCommitResponse:
    return SequenceCommitResponse(
        sequence_hash=None,
        outcome="incomplete",
        sequence_record_published=False,
        frames=frames,
    )


def test_sequence_handle_repr_redacts_the_ticket() -> None:
    handle = SequenceHandle(_SEQUENCE_ID, "super-secret-ticket")
    printed = repr(handle)
    assert "super-secret-ticket" not in printed
    assert str(_SEQUENCE_ID) in printed
    assert "ticket=[redacted]" in printed


def test_opened_sequence_holds_handle_and_head_frame_id() -> None:
    handle = SequenceHandle(_SEQUENCE_ID, "ticket")
    opened = OpenedSequence(handle, head_frame_id=1)
    assert opened.handle is handle
    assert opened.head_frame_id == 1


def test_sequence_open_request_accepts_no_expected_size() -> None:
    request = SequenceOpenRequest((), None)
    assert request.expected_size is None


def test_sequence_open_request_accepts_a_positive_expected_size() -> None:
    request = SequenceOpenRequest((), 5)
    assert request.expected_size == 5


def test_sequence_open_request_refuses_a_non_positive_expected_size() -> None:
    with pytest.raises(ValueError, match="expected_size must be above zero"):
        SequenceOpenRequest((), 0)


def test_sequence_batching_refuses_a_non_positive_max_request_bytes() -> None:
    with pytest.raises(ValueError, match="max_request_bytes must be above zero"):
        SequenceBatching(0, 1)


def test_sequence_batching_refuses_a_non_positive_max_frames_per_request() -> None:
    with pytest.raises(ValueError, match="max_frames_per_request must be above zero"):
        SequenceBatching(1, 0)


def test_sequence_batching_lists_both_bad_fields_together() -> None:
    with pytest.raises(ValueError) as excinfo:
        SequenceBatching(0, 0)
    message = str(excinfo.value)
    assert "max_request_bytes" in message
    assert "max_frames_per_request" in message


def test_sequence_register_options_accepts_valid_fields() -> None:
    batching = SequenceBatching(1024, 5)
    options = SequenceRegisterOptions(1.0, 3, batching)
    assert options.poll_interval == 1.0
    assert options.commit_attempts == 3
    assert options.batching is batching
    assert options.open is None
    assert options.existing is None


def test_sequence_register_options_refuses_a_non_positive_poll_interval() -> None:
    with pytest.raises(ValueError, match="poll_interval must be above zero"):
        SequenceRegisterOptions(0.0, 3, SequenceBatching(1024, 5))


def test_sequence_register_options_refuses_fewer_than_one_commit_attempt() -> None:
    with pytest.raises(ValueError, match="commit_attempts must be at least one"):
        SequenceRegisterOptions(1.0, 0, SequenceBatching(1024, 5))


def test_sequence_register_options_refuses_a_missing_batching() -> None:
    with pytest.raises(ValueError, match="batching is required"):
        SequenceRegisterOptions(1.0, 3, None)  # type: ignore[arg-type]


def test_sequence_register_options_lists_every_bad_field_together() -> None:
    with pytest.raises(ValueError) as excinfo:
        SequenceRegisterOptions(0.0, 0, None)  # type: ignore[arg-type]
    message = str(excinfo.value)
    assert "poll_interval" in message
    assert "commit_attempts" in message
    assert "batching" in message


def test_encoded_frame_holds_its_fields() -> None:
    frame = EncodedFrame(3, PxFrameType.BODY, b"bytes", b"\x00" * 32)
    assert frame.frame_id == 3
    assert frame.frame_type is PxFrameType.BODY
    assert frame.data == b"bytes"
    assert frame.frame_hash == b"\x00" * 32


def test_sequence_verdict_error_names_gaps_errata_and_connected() -> None:
    verdict = _verdict(gaps=[object()], errata=[object(), object()], connected=False)
    error = SequenceVerdictError(verdict)
    assert error.verdict is verdict
    message = str(error)
    assert "1 gap(s)" in message
    assert "2 errata" in message
    assert "connected = False" in message


def test_sequence_verdict_error_never_names_a_ticket() -> None:
    verdict = _verdict(connected=True)
    message = str(SequenceVerdictError(verdict))
    assert "ticket" not in message.lower()


def test_sequence_commit_error_counts_published_and_unpublished_frames() -> None:
    frames = [
        SequenceCommitFrameResponse(frame_id=1, state="published", original_image_hash="abc", refusal_name=None),
        SequenceCommitFrameResponse(frame_id=2, state="notPublished", original_image_hash=None, refusal_name=None),
        SequenceCommitFrameResponse(frame_id=3, state="notPublished", original_image_hash=None, refusal_name=None),
    ]
    error = SequenceCommitError(_commit(frames))
    assert error.commit.frames == frames
    message = str(error)
    assert "1 frame(s) published" in message
    assert "2 unpublished" in message


def test_sequence_commit_error_never_names_a_ticket() -> None:
    frames = [SequenceCommitFrameResponse(frame_id=1, state="notPublished", original_image_hash=None, refusal_name=None)]
    message = str(SequenceCommitError(_commit(frames)))
    assert "ticket" not in message.lower()
