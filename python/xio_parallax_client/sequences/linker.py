"""Derives the prev/next links a frame source carries no opinion about, one frame of lookahead.

Mirrors the .NET client's `SequenceChainLinker`: the first frame's prev is the sequence's HEAD id,
each frame's next is the id of the frame read immediately after it, and the last frame's next is
therefore the END id (its own id plus one).
"""

# PC-112: the sequence conversation's chain linker, sync and async

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from dataclasses import dataclass

from ..frames.source import SequenceFrameInput


# PC-112: one source frame with its derived links
@dataclass(frozen=True, slots=True)
class LinkedFrame:
    """One source frame with its derived prev and next link."""

    frame: SequenceFrameInput
    prev: int
    next: int


def _refuse_unless_above(frame_id: int, previous_id: int) -> None:
    """Raise `ValueError` naming both ids when `frame_id` is not above `previous_id`."""
    if frame_id <= previous_id:
        raise ValueError(f"frame id {frame_id} is not above {previous_id}")


# PC-112: the sync chain linker, one frame of lookahead
def link_frames(frames: Iterable[SequenceFrameInput], head_frame_id: int) -> Iterator[LinkedFrame]:
    """Yield each frame from `frames` with its derived prev/next link, one frame of lookahead.

    A frame whose id is not above the frame read immediately before it (or, for the first frame,
    not above `head_frame_id`) raises `ValueError` naming both ids, before the frame ahead of it is
    yielded, so no link ever names the offending id. An empty source yields nothing.
    """
    iterator = iter(frames)
    try:
        current = next(iterator)
    except StopIteration:
        return
    previous_id = head_frame_id
    _refuse_unless_above(current.frame_id, previous_id)
    for following in iterator:
        _refuse_unless_above(following.frame_id, current.frame_id)
        yield LinkedFrame(current, previous_id, following.frame_id)
        previous_id = current.frame_id
        current = following
    yield LinkedFrame(current, previous_id, current.frame_id + 1)


# PC-112: the async mirror of link_frames, for an AsyncSequenceFrameSource
async def link_frames_async(
    frames: AsyncIterable[SequenceFrameInput], head_frame_id: int
) -> AsyncIterator[LinkedFrame]:
    """The async mirror of `link_frames`, for an `AsyncSequenceFrameSource`."""
    iterator = frames.__aiter__()
    try:
        current = await iterator.__anext__()
    except StopAsyncIteration:
        return
    previous_id = head_frame_id
    _refuse_unless_above(current.frame_id, previous_id)
    async for following in iterator:
        _refuse_unless_above(following.frame_id, current.frame_id)
        yield LinkedFrame(current, previous_id, following.frame_id)
        previous_id = current.frame_id
        current = following
    yield LinkedFrame(current, previous_id, current.frame_id + 1)


# PC-112: bundles both directions behind the one HEAD id they link from
class ChainLinker:
    """Bundles `link_frames`/`link_frames_async` behind the one sequence HEAD id they link from."""

    def __init__(self, head_frame_id: int) -> None:
        """Hold the sequence's HEAD id, the first frame's prev link."""
        self._head_frame_id = head_frame_id

    def link_frames(self, frames: Iterable[SequenceFrameInput]) -> Iterator[LinkedFrame]:
        """Yield `frames` linked from this sequence's HEAD id; see the module-level `link_frames`."""
        return link_frames(frames, self._head_frame_id)

    def link_frames_async(self, frames: AsyncIterable[SequenceFrameInput]) -> AsyncIterator[LinkedFrame]:
        """The async mirror of `link_frames`; see the module-level `link_frames_async`."""
        return link_frames_async(frames, self._head_frame_id)
