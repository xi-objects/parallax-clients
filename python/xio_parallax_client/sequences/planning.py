"""Pure decisions the sequence conversation makes: frame batching, resume selection, committability.

None of this module does I/O; the conversation shell (PC-114) drives `FrameBatchPlanner` frame by
frame as it streams and encodes a source, and calls `is_selected_for_resume` / `is_committable`
with values read off the server's own responses.
"""

# PC-112: the sequence conversation's pure decision layer

from __future__ import annotations

from collections.abc import Sequence

from ..frames.protocol import PxGapRange
from ..multipart import build_sequence_frame_parts, measure_multipart
from .encoding import EncodedFrame


def _refuse_non_positive(name: str, value: int) -> None:
    """Raise `ValueError` naming `name` when `value` is not above zero."""
    if value <= 0:
        raise ValueError(f"{name} must be above zero; was {value}")


# PC-112: batches encoded frames under a whole-body byte cap and a frame-count cap, with no I/O
class FrameBatchPlanner:
    """Accumulates encoded frames into batches under a byte cap and a frame-count cap, with no I/O.

    Each batch's byte cost is the whole multipart body `multipart.build_sequence_frame_parts` and
    `multipart.measure_multipart` compute for it (parts, part headers, boundaries, the closing
    delimiter), not a per-frame estimate: the appended cost of a frame is the cost of a two-frame
    body minus the cost of a one-frame body, mirroring the .NET client. A frame whose own body
    alone would exceed `max_request_bytes` raises `ValueError` naming its id, before it or any
    batch holding it is returned.
    """

    def __init__(self, max_request_bytes: int, max_frames_per_request: int) -> None:
        """Hold the two caps every batch this planner returns stays under."""
        _refuse_non_positive("max_request_bytes", max_request_bytes)
        _refuse_non_positive("max_frames_per_request", max_frames_per_request)
        self._max_request_bytes = max_request_bytes
        self._max_frames_per_request = max_frames_per_request
        self._batch: list[EncodedFrame] = []
        self._batch_bytes = 0

    # PC-112: adds one frame, closing and returning the open batch first when it would not fit
    def add(self, frame: EncodedFrame) -> list[EncodedFrame] | None:
        """Add one encoded frame; return a batch ready to send, or `None` when it joined the open one."""
        alone = measure_multipart(build_sequence_frame_parts([frame]))
        if alone > self._max_request_bytes:
            raise ValueError(
                f"frame {frame.frame_id} alone makes a {alone}-byte request, "
                f"above max_request_bytes {self._max_request_bytes}"
            )
        appended = measure_multipart(build_sequence_frame_parts([frame, frame])) - alone
        would_overflow_count = len(self._batch) + 1 > self._max_frames_per_request
        would_overflow_bytes = self._batch_bytes + appended > self._max_request_bytes
        flushed: list[EncodedFrame] | None = None
        if self._batch and (would_overflow_count or would_overflow_bytes):
            flushed = self._batch
            self._batch = []
            self._batch_bytes = 0
        self._batch_bytes = alone if not self._batch else self._batch_bytes + appended
        self._batch.append(frame)
        return flushed

    # PC-112: returns and clears whatever partial batch remains once the source is exhausted
    def flush(self) -> list[EncodedFrame] | None:
        """Return and clear the final partial batch, or `None` when nothing is pending."""
        if not self._batch:
            return None
        remaining = self._batch
        self._batch = []
        self._batch_bytes = 0
        return remaining


# PC-112: a resumed sequence re-sends a frame above the reach or inside a gap, nothing else
def is_selected_for_resume(frame_id: int, reach: int, gaps: Sequence[PxGapRange]) -> bool:
    """`True` when `frame_id` is above `reach` or inside any inclusive range of `gaps`."""
    return frame_id > reach or any(gap.range_from <= frame_id <= gap.range_to for gap in gaps)


# PC-112: a sealed sequence is committable only when its walk is connected, gapless and errata-free
def is_committable(connected: bool, gap_count: int, errata_count: int) -> bool:
    """`True` only when `connected` and both `gap_count` and `errata_count` are zero."""
    return connected and gap_count == 0 and errata_count == 0
