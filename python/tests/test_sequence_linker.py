"""PC-112: the chain linker derives prev/next with one frame of lookahead, sync and async."""

from __future__ import annotations

from datetime import timedelta

import pytest
from xio_parallax_client.frames.protocol import PxBucketContent
from xio_parallax_client.frames.source import SequenceFrameInput
from xio_parallax_client.sequences.linker import ChainLinker, link_frames, link_frames_async


def _frame(frame_id: int) -> SequenceFrameInput:
    return SequenceFrameInput(frame_id, timedelta(0), (PxBucketContent("IMAG", b"x"),))


async def _collect_async(frames: list[SequenceFrameInput], head_frame_id: int) -> list:
    async def source():
        for frame in frames:
            yield frame

    return [item async for item in link_frames_async(source(), head_frame_id)]


def test_three_frames_with_room_link_from_head_to_end() -> None:
    frames = [_frame(2), _frame(5), _frame(9)]
    linked = list(link_frames(frames, head_frame_id=1))
    assert [(link.frame.frame_id, link.prev, link.next) for link in linked] == [
        (2, 1, 5),
        (5, 2, 9),
        (9, 5, 10),
    ]


def test_a_single_frame_links_from_head_to_its_own_id_plus_one() -> None:
    linked = list(link_frames([_frame(3)], head_frame_id=1))
    assert [(link.frame.frame_id, link.prev, link.next) for link in linked] == [(3, 1, 4)]


def test_empty_source_yields_nothing() -> None:
    assert list(link_frames([], head_frame_id=1)) == []


def test_a_non_monotone_id_is_refused_before_the_frame_ahead_of_it_is_yielded() -> None:
    frames = [_frame(5), _frame(5)]
    generator = link_frames(frames, head_frame_id=1)
    with pytest.raises(ValueError, match="frame id 5 is not above 5"):
        list(generator)


def test_a_first_frame_not_above_head_is_refused_naming_both_ids() -> None:
    with pytest.raises(ValueError, match="frame id 1 is not above 1"):
        list(link_frames([_frame(1)], head_frame_id=1))


def test_chain_linker_bundles_sync_linking_behind_its_head_id() -> None:
    linker = ChainLinker(head_frame_id=1)
    linked = list(linker.link_frames([_frame(2), _frame(4)]))
    assert [(link.frame.frame_id, link.prev, link.next) for link in linked] == [(2, 1, 4), (4, 2, 5)]


@pytest.mark.asyncio
async def test_async_three_frames_with_room_link_from_head_to_end() -> None:
    linked = await _collect_async([_frame(2), _frame(5), _frame(9)], head_frame_id=1)
    assert [(link.frame.frame_id, link.prev, link.next) for link in linked] == [
        (2, 1, 5),
        (5, 2, 9),
        (9, 5, 10),
    ]


@pytest.mark.asyncio
async def test_async_empty_source_yields_nothing() -> None:
    assert await _collect_async([], head_frame_id=1) == []


@pytest.mark.asyncio
async def test_async_non_monotone_id_is_refused_naming_both_ids() -> None:
    with pytest.raises(ValueError, match="frame id 5 is not above 5"):
        await _collect_async([_frame(5), _frame(5)], head_frame_id=1)


@pytest.mark.asyncio
async def test_chain_linker_bundles_async_linking_behind_its_head_id() -> None:
    linker = ChainLinker(head_frame_id=1)

    async def source():
        yield _frame(2)
        yield _frame(4)

    linked = [item async for item in linker.link_frames_async(source())]
    assert [(link.frame.frame_id, link.prev, link.next) for link in linked] == [(2, 1, 4), (4, 2, 5)]
