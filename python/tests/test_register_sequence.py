"""The fresh register conversation: batching, links, END, the verdict and commit retries.

Mirrors `RegisterSequenceTests` (.NET): batching by the whole request body's bytes, a verdict-less
END refused, errata refused before commit, and an incomplete commit retried under
`SequenceRegisterOptions.commit_attempts`. The helpers here (`source`, `register_options`,
`build_client`, `verdict_json`, `commit_response`) are reused by `test_register_sequence_resume.py`
and `test_register_sequence_refusals.py`, the way .NET's `RegisterSequenceTests` statics are reused
by its resume and refusal test classes.
"""

# PC-114: the fresh register conversation, sync

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

import httpx
import pytest
import respx
from xio_parallax_client import (
    ParallaxClient,
    ParallaxClientError,
    ParallaxClientOptions,
    SequenceBatching,
    SequenceCommitError,
    SequenceOpenRequest,
    SequenceRegisterOptions,
    SequenceVerdictError,
)
from xio_parallax_client.frames.source import SequenceFrameInput

from .conftest import BASE_URL
from .sequence_server import TICKET, SequenceConversationServer

_OPEN_REQUEST = SequenceOpenRequest((), None)


# PC-114: a fixed source of frames, one per given id, mirroring .NET's FakeSequenceFrameSource
@dataclass(frozen=True, slots=True)
class ListFrameSource:
    """A `SequenceFrameSource` over a fixed list of frame ids, one small image bucket each."""

    frame_ids: tuple[int, ...]

    def read_frames(self) -> Iterable[SequenceFrameInput]:
        """Yield one `SequenceFrameInput` per id, read afresh (a fresh list) on every call."""
        return [
            SequenceFrameInput.for_image(
                frame_id, timedelta(milliseconds=40 * frame_id), bytes([frame_id % 256, 7, 7])
            )
            for frame_id in self.frame_ids
        ]


def source(*frame_ids: int) -> ListFrameSource:
    """A source yielding one frame per given id, in order."""
    return ListFrameSource(frame_ids)


def register_options(
    max_frames_per_request: int, commit_attempts: int = 1, max_request_bytes: int = 1_000_000
) -> SequenceRegisterOptions:
    """Fresh-open options: a 1ms poll interval and the given batching caps."""
    return SequenceRegisterOptions(
        poll_interval=0.001,
        commit_attempts=commit_attempts,
        batching=SequenceBatching(max_request_bytes, max_frames_per_request),
        open=_OPEN_REQUEST,
    )


def build_client(_server: SequenceConversationServer) -> ParallaxClient:
    """A `ParallaxClient` against the fake base URL `_server` answers."""
    return ParallaxClient(ParallaxClientOptions(account_token="test-token", base_url=BASE_URL))


def verdict_json(state: str, connected: bool, reach: int, gaps: str = "[]", errata: str = "[]") -> str:
    """A verdict document shaped as the API declares it, for the fake server's scripted answers."""
    return (
        f'{{"state": "{state}", "framesReceived": {reach}, "expectedSize": null, "reach": {reach}, '
        f'"gaps": {gaps}, "errata": {errata}, "connected": {"true" if connected else "false"}}}'
    )


def verdict_response(state: str, connected: bool, reach: int, gaps: str = "[]", errata: str = "[]") -> httpx.Response:
    """A `verdict_json` document wrapped as the `progress` route answers it."""
    body = verdict_json(state, connected, reach, gaps, errata)
    return httpx.Response(200, content=body, headers={"content-type": "application/json"})


def commit_response(outcome: str, *frame_states: str) -> httpx.Response:
    """A commit document shaped as the API declares it, with the given frame states in order."""
    frames = ", ".join(
        f'{{"frameId": {index + 1}, "state": "{state}", "originalImageHash": null, "refusalName": null}}'
        for index, state in enumerate(frame_states)
    )
    sequence_hash = "null" if outcome == "incomplete" else '"sequence-hash"'
    published = "false" if outcome == "incomplete" else "true"
    body = (
        f'{{"sequenceHash": {sequence_hash}, "outcome": "{outcome}", '
        f'"sequenceRecordPublished": {published}, "frames": [{frames}]}}'
    )
    return httpx.Response(200, content=body, headers={"content-type": "application/json"})


def frames_requests(server: SequenceConversationServer) -> list[httpx.Request]:
    """Every `/frames` request `server` answered, in order."""
    prefix = f"/sequences/{server.sequence_id}"
    return [call.request for call in respx.calls if call.request.url.path == f"{prefix}/frames"]


@respx.mock
def test_three_frames_under_two_per_request_upload_as_two_batches_then_end_then_commit_and_results() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=4)
    server.commits.append(commit_response("registered", "published", "published", "published"))
    client = build_client(server)
    reports: list[object] = []

    result = client.register_sequence(source(1, 2, 3), register_options(max_frames_per_request=2), reports.append)

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [
        "POST /sequences",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/commit",
        f"GET {prefix}/results",
    ]
    open_request = next(call.request for call in respx.calls if call.request.url.path == "/sequences")
    assert "x-sequence-ticket" not in {name.lower() for name in open_request.headers}
    for request in frames_requests(server):
        assert request.headers["x-sequence-ticket"] == TICKET

    batches = server.decode_uploads()
    assert len(batches) == 3
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in batches[0]] == [
        ("BODY", 1, 0, 2),
        ("BODY", 2, 1, 3),
    ]
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in batches[1]] == [("BODY", 3, 2, 4)]
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in batches[2]] == [("END", 4, 3, None)]

    assert result.sequence == server.opened
    assert result.verdict.connected is True
    assert result.commit.outcome == "registered"
    assert result.results.outcome == "registered"
    assert len(reports) == 1
    assert reports[0] is result.verdict


@respx.mock
def test_the_request_byte_cap_splits_batches_at_the_whole_multipart_body_length() -> None:
    calibration = _run_to_results(max_frames_per_request=2, max_request_bytes=1_000_000)
    two_frame_body = len(frames_requests(calibration)[0].content)

    at_the_bound = _run_to_results(max_frames_per_request=8, max_request_bytes=two_frame_body)
    assert at_the_bound.uploaded_frame_ids() == [[1, 2], [3], [4]]
    for request in frames_requests(at_the_bound):
        assert len(request.content) <= two_frame_body

    below_the_bound = _run_to_results(max_frames_per_request=8, max_request_bytes=two_frame_body - 1)
    assert below_the_bound.uploaded_frame_ids() == [[1], [2], [3], [4]]
    for request in frames_requests(below_the_bound):
        assert len(request.content) <= two_frame_body - 1


def _run_to_results(max_frames_per_request: int, max_request_bytes: int) -> SequenceConversationServer:
    """A fresh server scripted to seal 1, 2, 3 with END 4 and register, run under the given caps."""
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=4)
    server.commits.append(commit_response("registered", "published", "published", "published"))
    client = build_client(server)
    client.register_sequence(
        source(1, 2, 3), register_options(max_frames_per_request, max_request_bytes=max_request_bytes)
    )
    return server


@respx.mock
def test_an_end_batch_answered_without_a_verdict_raises_naming_the_end_id_and_commits_nothing() -> None:
    server = SequenceConversationServer(BASE_URL)
    client = build_client(server)
    reports: list[object] = []

    with pytest.raises(ParallaxClientError) as excinfo:
        client.register_sequence(source(1), register_options(max_frames_per_request=2), reports.append)

    assert "END frame 2" in str(excinfo.value)
    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == ["POST /sequences", f"POST {prefix}/frames", f"POST {prefix}/frames"]
    assert reports == []


@respx.mock
def test_a_sealing_verdict_naming_errata_raises_it_and_commits_nothing() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.errata_frame_ids.add(2)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json(
        "sealed", connected=True, reach=4, errata='[{"frameId": 2, "originalImageHash": "original-image-hash-2"}]'
    )
    client = build_client(server)

    with pytest.raises(SequenceVerdictError) as excinfo:
        client.register_sequence(source(1, 2, 3), register_options(max_frames_per_request=8))

    errata = excinfo.value.verdict.errata
    assert len(errata) == 1
    assert errata[0].frame_id == 2
    assert errata[0].original_image_hash == "original-image-hash-2"
    assert "1 errata" in str(excinfo.value)
    assert not any(call.endswith("/commit") for call in server.calls)


@respx.mock
def test_a_sealing_verdict_with_a_gap_raises_it_and_commits_nothing() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json("sealed", connected=False, reach=1, gaps='[{"from": 2, "to": 2}]')
    client = build_client(server)

    with pytest.raises(SequenceVerdictError) as excinfo:
        client.register_sequence(source(1, 2, 3), register_options(max_frames_per_request=8))

    gap = excinfo.value.verdict.gaps
    assert len(gap) == 1
    assert gap[0].from_ == 2
    assert not any(call.endswith("/commit") for call in server.calls)


@respx.mock
def test_an_incomplete_commit_is_called_again_after_the_poll_interval_until_registered() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 2
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=2)
    server.commits.append(commit_response("incomplete", "notPublished"))
    server.commits.append(commit_response("registered", "published"))
    client = build_client(server)

    result = client.register_sequence(source(1), register_options(max_frames_per_request=8, commit_attempts=2))

    assert result.commit.outcome == "registered"
    assert sum(1 for call in server.calls if call.endswith("/commit")) == 2
    assert server.calls[-1].endswith("/results")


@respx.mock
def test_a_commit_still_incomplete_after_every_attempt_raises_after_exactly_that_many_calls() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 3
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=3)
    server.commits.append(commit_response("incomplete", "published", "notPublished"))
    server.commits.append(commit_response("incomplete", "published", "notPublished"))
    client = build_client(server)

    with pytest.raises(SequenceCommitError) as excinfo:
        client.register_sequence(source(1, 2), register_options(max_frames_per_request=8, commit_attempts=2))

    assert excinfo.value.commit.outcome == "incomplete"
    assert sum(1 for call in server.calls if call.endswith("/commit")) == 2
    assert not any(call.endswith("/results") for call in server.calls)
    assert TICKET not in str(excinfo.value)
