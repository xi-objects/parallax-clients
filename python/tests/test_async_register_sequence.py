"""The async mirror of the register conversation: the core path, a resume, and an
`AsyncSequenceFrameSource`.

Mirrors `test_register_sequence.py` / `test_register_sequence_resume.py`, run through
`AsyncParallaxClient.register_sequence`, plus the async-source preference `register_sequence`
gives an `AsyncSequenceFrameSource` over a plain `SequenceFrameSource`.
"""

# PC-114: the register conversation's async mirror, core path, a resume, and an async source

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterable, Iterable
from dataclasses import dataclass
from datetime import timedelta

import pytest
import respx
from xio_parallax_client import AsyncParallaxClient, ParallaxClientError, ParallaxClientOptions, SequenceCommitError
from xio_parallax_client.frames.source import SequenceFrameInput

from .conftest import BASE_URL
from .sequence_server import SequenceConversationServer
from .test_register_sequence import commit_response, register_options, source, verdict_json, verdict_response


def _build_async_client(_server: SequenceConversationServer) -> AsyncParallaxClient:
    """An `AsyncParallaxClient` against the fake base URL `_server` answers."""
    return AsyncParallaxClient(ParallaxClientOptions(account_token="test-token", base_url=BASE_URL))


# PC-114: an AsyncSequenceFrameSource, the async mirror of test_register_sequence's ListFrameSource
@dataclass(frozen=True, slots=True)
class AsyncListFrameSource:
    """An `AsyncSequenceFrameSource` over a fixed list of frame ids, one small image bucket each."""

    frame_ids: tuple[int, ...]

    async def read_frames_async(self) -> AsyncIterable[SequenceFrameInput]:
        """Yield one `SequenceFrameInput` per id, read afresh (a fresh list) on every call."""
        for frame_id in self.frame_ids:
            yield SequenceFrameInput.for_image(
                frame_id, timedelta(milliseconds=40 * frame_id), bytes([frame_id % 256, 7, 7])
            )


# PC-114: an object satisfying both frame source protocols; the async one must be preferred
@dataclass(frozen=True, slots=True)
class BothProtocolsFrameSource:
    """Implements both `SequenceFrameSource` and `AsyncSequenceFrameSource`; only the sync side raises."""

    frame_ids: tuple[int, ...]

    def read_frames(self) -> Iterable[SequenceFrameInput]:
        """Never called: the async side is preferred whenever both are implemented."""
        raise AssertionError("the sync read_frames was called although an async source was preferred")

    async def read_frames_async(self) -> AsyncIterable[SequenceFrameInput]:
        """Yield one `SequenceFrameInput` per id, exactly as `AsyncListFrameSource` does."""
        for frame_id in self.frame_ids:
            yield SequenceFrameInput.for_image(
                frame_id, timedelta(milliseconds=40 * frame_id), bytes([frame_id % 256, 7, 7])
            )


@pytest.mark.asyncio
@respx.mock
async def test_three_frames_under_two_per_request_upload_as_two_batches_then_end_then_commit_and_results() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=4)
    server.commits.append(commit_response("registered", "published", "published", "published"))
    client = _build_async_client(server)
    reports: list[object] = []

    result = await client.register_sequence(source(1, 2, 3), register_options(max_frames_per_request=2), reports.append)

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [
        "POST /sequences",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/commit",
        f"GET {prefix}/results",
    ]
    assert server.uploaded_frame_ids() == [[1, 2], [3], [4]]
    assert result.sequence == server.opened
    assert result.commit.outcome == "registered"
    assert len(reports) == 1


@pytest.mark.asyncio
@respx.mock
async def test_a_commit_still_incomplete_after_every_attempt_raises_after_exactly_that_many_calls() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 3
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=3)
    server.commits.append(commit_response("incomplete", "published", "notPublished"))
    server.commits.append(commit_response("incomplete", "published", "notPublished"))
    client = _build_async_client(server)

    with pytest.raises(SequenceCommitError) as excinfo:
        await client.register_sequence(source(1, 2), register_options(max_frames_per_request=8, commit_attempts=2))

    assert excinfo.value.commit.outcome == "incomplete"
    assert sum(1 for call in server.calls if call.endswith("/commit")) == 2


@pytest.mark.asyncio
@respx.mock
async def test_resuming_an_open_sequence_uploads_only_the_frames_in_a_gap_or_above_the_reach_then_end() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("open", connected=False, reach=3))
    server.gaps_json = '{"gaps": [{"from": 4, "to": 4, "gapFrame": "AAA="}]}'
    server.sealing_frame_id = 7
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=7)
    server.commits.append(commit_response("registered", "published"))
    client = _build_async_client(server)
    resume_options = dataclasses.replace(
        register_options(max_frames_per_request=8), open=None, existing=server.opened
    )

    result = await client.register_sequence(source(1, 2, 3, 4, 5, 6), resume_options)

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [
        f"GET {prefix}/progress",
        f"GET {prefix}/gaps",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/commit",
        f"GET {prefix}/results",
    ]
    assert server.uploaded_frame_ids() == [[4, 5, 6], [7]]
    assert result.sequence == server.opened


@pytest.mark.asyncio
@respx.mock
async def test_resuming_an_abandoned_sequence_raises_naming_the_state() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("abandoned", connected=False, reach=2))
    client = _build_async_client(server)
    resume_options = dataclasses.replace(
        register_options(max_frames_per_request=8), open=None, existing=server.opened
    )

    with pytest.raises(ParallaxClientError) as excinfo:
        await client.register_sequence(source(1, 2, 3), resume_options)

    assert "abandoned" in str(excinfo.value)
    assert server.calls == [f"GET /sequences/{server.sequence_id}/progress"]


@pytest.mark.asyncio
@respx.mock
async def test_an_async_source_is_read_through_read_frames_async() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 2
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=2)
    server.commits.append(commit_response("registered", "published"))
    client = _build_async_client(server)

    result = await client.register_sequence(AsyncListFrameSource((1,)), register_options(max_frames_per_request=8))

    assert server.uploaded_frame_ids() == [[1], [2]]
    assert result.commit.outcome == "registered"


@pytest.mark.asyncio
@respx.mock
async def test_a_source_implementing_both_protocols_is_read_through_the_async_side() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 2
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=2)
    server.commits.append(commit_response("registered", "published"))
    client = _build_async_client(server)

    result = await client.register_sequence(
        BothProtocolsFrameSource((1,)), register_options(max_frames_per_request=8)
    )

    assert server.uploaded_frame_ids() == [[1], [2]]
    assert result.commit.outcome == "registered"
