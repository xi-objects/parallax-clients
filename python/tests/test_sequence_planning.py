"""PC-112: pure batching, resume selection and committability, no I/O."""

from __future__ import annotations

import pytest
from xio_parallax_client.frames.protocol import PxFrameType, PxGapRange
from xio_parallax_client.multipart import build_sequence_frame_parts, measure_multipart
from xio_parallax_client.sequences.encoding import EncodedFrame
from xio_parallax_client.sequences.planning import FrameBatchPlanner, is_committable, is_selected_for_resume


def _frame(frame_id: int, size: int) -> EncodedFrame:
    return EncodedFrame(frame_id, PxFrameType.BODY, b"x" * size, b"\x00" * 32)


def test_batches_close_at_the_frame_count_cap() -> None:
    frames = [_frame(1, 10), _frame(2, 10), _frame(3, 10)]
    planner = FrameBatchPlanner(max_request_bytes=10_000, max_frames_per_request=2)

    assert planner.add(frames[0]) is None
    assert planner.add(frames[1]) is None
    flushed = planner.add(frames[2])

    assert flushed == frames[:2]
    assert planner.flush() == [frames[2]]


def test_batches_close_at_the_whole_body_byte_cap() -> None:
    f1, f2, f3 = _frame(1, 100), _frame(2, 100), _frame(3, 100)
    cap = measure_multipart(build_sequence_frame_parts([f1, f2]))
    planner = FrameBatchPlanner(max_request_bytes=cap, max_frames_per_request=100)

    assert planner.add(f1) is None
    assert planner.add(f2) is None
    flushed = planner.add(f3)

    assert flushed == [f1, f2]
    assert planner.flush() == [f3]


def test_a_frame_alone_over_the_byte_cap_is_refused_naming_its_id() -> None:
    frame = _frame(9, 500)
    alone = measure_multipart(build_sequence_frame_parts([frame]))
    planner = FrameBatchPlanner(max_request_bytes=alone - 1, max_frames_per_request=10)

    with pytest.raises(ValueError, match=r"frame 9 alone makes a \d+-byte request"):
        planner.add(frame)


def test_earlier_batches_are_unaffected_by_a_later_oversized_frame() -> None:
    small, big = _frame(1, 10), _frame(2, 10_000)
    alone_big = measure_multipart(build_sequence_frame_parts([big]))
    planner = FrameBatchPlanner(max_request_bytes=alone_big - 1, max_frames_per_request=10)

    assert planner.add(small) is None
    with pytest.raises(ValueError, match="frame 2"):
        planner.add(big)
    assert planner.flush() == [small]


def test_non_positive_caps_are_refused_naming_the_field() -> None:
    with pytest.raises(ValueError, match="max_request_bytes must be above zero"):
        FrameBatchPlanner(max_request_bytes=0, max_frames_per_request=1)
    with pytest.raises(ValueError, match="max_frames_per_request must be above zero"):
        FrameBatchPlanner(max_request_bytes=1, max_frames_per_request=0)


def test_flush_with_nothing_pending_answers_none() -> None:
    planner = FrameBatchPlanner(max_request_bytes=1_000, max_frames_per_request=10)
    assert planner.flush() is None


@pytest.mark.parametrize(
    ("frame_id", "reach", "gaps", "expected"),
    [
        (6, 5, [], True),
        (5, 5, [], False),
        (3, 5, [PxGapRange(3, 4)], True),
        (2, 5, [PxGapRange(3, 4)], False),
        (4, 5, [PxGapRange(3, 4)], True),
    ],
)
def test_resume_selection_above_reach_or_in_gap(frame_id: int, reach: int, gaps: list, expected: bool) -> None:
    assert is_selected_for_resume(frame_id, reach, gaps) is expected


@pytest.mark.parametrize(
    ("connected", "gap_count", "errata_count", "expected"),
    [
        (True, 0, 0, True),
        (False, 0, 0, False),
        (True, 1, 0, False),
        (True, 0, 1, False),
    ],
)
def test_is_committable_true_only_when_connected_gapless_and_errata_free(
    connected: bool, gap_count: int, errata_count: int, expected: bool
) -> None:
    assert is_committable(connected, gap_count, errata_count) is expected
