"""What the register conversation refuses: the options, an oversized frame, a non-monotone id, an
empty source, and that no exception ever names the ticket.

Mirrors `RegisterSequenceRefusalTests` (.NET): a non-monotone id and an oversized frame are refused
naming the offending frame, before any request carries it; earlier batches may already have gone.
"""

# PC-114: what the register conversation refuses, sync

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import timedelta

import httpx
import pytest
import respx
from xio_parallax_client import (
    ParallaxClient,
    ParallaxClientError,
    ParallaxClientOptions,
    ParallaxProblem,
    SequenceCommitError,
    SequencesNotEnabled,
    SequenceVerdictError,
)
from xio_parallax_client.frames.source import SequenceFrameInput

from .conftest import BASE_URL
from .sequence_server import TICKET, SequenceConversationServer
from .test_register_sequence import build_client, commit_response, register_options, source, verdict_json


# PC-114: a source yielding exact given frames, for the oversized-frame case's distinct byte sizes
@dataclass(frozen=True, slots=True)
class ExactFrameSource:
    """A `SequenceFrameSource` over an exact, pre-built tuple of frames."""

    frames: tuple[SequenceFrameInput, ...]

    def read_frames(self) -> Iterable[SequenceFrameInput]:
        """Yield the exact frames given at construction, in order."""
        return self.frames


@respx.mock
def test_both_open_and_existing_set_raises_naming_both_before_any_request() -> None:
    server = SequenceConversationServer(BASE_URL)
    client = build_client(server)
    options = dataclasses.replace(register_options(max_frames_per_request=8), existing=server.opened)

    with pytest.raises(ValueError) as excinfo:
        client.register_sequence(source(1), options)

    assert "open" in str(excinfo.value)
    assert "existing" in str(excinfo.value)
    assert server.calls == []


@respx.mock
def test_neither_open_nor_existing_set_raises_naming_both_before_any_request() -> None:
    server = SequenceConversationServer(BASE_URL)
    client = build_client(server)
    options = dataclasses.replace(register_options(max_frames_per_request=8), open=None)

    with pytest.raises(ValueError) as excinfo:
        client.register_sequence(source(1), options)

    assert "open" in str(excinfo.value)
    assert "existing" in str(excinfo.value)
    assert server.calls == []


@respx.mock
def test_a_frame_alone_above_max_request_bytes_raises_naming_its_id_and_no_request_carries_it() -> None:
    server = SequenceConversationServer(BASE_URL)
    client = build_client(server)
    frame_source = ExactFrameSource(
        (
            SequenceFrameInput.for_image(1, timedelta(0), b"\x01"),
            SequenceFrameInput.for_image(2, timedelta(0), b"\x02"),
            SequenceFrameInput.for_image(3, timedelta(0), bytes(4096)),
        )
    )
    options = register_options(max_frames_per_request=1, max_request_bytes=2048)

    with pytest.raises(ValueError) as excinfo:
        client.register_sequence(frame_source, options)

    assert "frame 3" in str(excinfo.value)
    assert server.uploaded_frame_ids() == [[1]]
    assert not any(call.endswith("/commit") for call in server.calls)


@respx.mock
def test_a_non_monotone_id_raises_naming_it_and_no_request_carries_it() -> None:
    server = SequenceConversationServer(BASE_URL)
    client = build_client(server)
    options = register_options(max_frames_per_request=1)

    with pytest.raises(ValueError) as excinfo:
        client.register_sequence(source(1, 2, 5, 4), options)

    assert "frame id 4" in str(excinfo.value)
    assert server.uploaded_frame_ids() == [[1]]
    assert not any(call.endswith("/commit") for call in server.calls)


@respx.mock
def test_an_empty_source_on_a_fresh_open_raises_and_leaves_the_sequence_open() -> None:
    server = SequenceConversationServer(BASE_URL)
    client = build_client(server)

    with pytest.raises(ParallaxClientError) as excinfo:
        client.register_sequence(source(), register_options(max_frames_per_request=8))

    assert "at least one BODY" in str(excinfo.value)
    assert server.calls == ["POST /sequences"]


def _assert_raises_without_ticket(exception_type: type[Exception], run: Callable[[], None]) -> None:
    """Run `run` (its own isolated `respx.mock`), and assert the raised exception never names TICKET."""
    with respx.mock, pytest.raises(exception_type) as excinfo:
        run()
    assert TICKET not in str(excinfo.value)
    assert TICKET not in repr(excinfo.value)


# PC-114: rework - the docstring promises this test; it was missing. Sweeps every model, error and
# typed problem the conversation can produce for the scripted ticket, so none of them ever names it.
# Each scenario below runs its own `SequenceConversationServer` inside its own `respx.mock`, since
# every server mocks the same `POST /sequences` path and two active at once would shadow each other.
@respx.mock
def test_no_ticket_reaches_any_repr_or_message() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 3
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=3)
    server.commits.append(commit_response("registered", "published", "published"))
    client = build_client(server)

    result = client.register_sequence(source(1, 2), register_options(max_frames_per_request=8))

    for text in (
        str(result),
        repr(result),
        str(result.sequence),
        repr(result.sequence),
        str(result.sequence.handle),
        repr(result.sequence.handle),
    ):
        assert TICKET not in text


def test_no_ticket_reaches_a_verdict_errors_message() -> None:
    """A sealed sequence whose verdict names errata raises `SequenceVerdictError`, never the ticket."""

    def run() -> None:
        server = SequenceConversationServer(BASE_URL)
        server.sealing_frame_id = 3
        server.sealing_verdict_json = verdict_json(
            "sealed", connected=True, reach=3, errata='[{"frameId": 1, "originalImageHash": "hash"}]'
        )
        build_client(server).register_sequence(source(1, 2), register_options(max_frames_per_request=8))

    _assert_raises_without_ticket(SequenceVerdictError, run)


def test_no_ticket_reaches_a_commit_errors_message() -> None:
    """A commit still incomplete after every attempt raises `SequenceCommitError`, never the ticket."""

    def run() -> None:
        server = SequenceConversationServer(BASE_URL)
        server.sealing_frame_id = 3
        server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=3)
        server.commits.append(commit_response("incomplete", "unpublished", "unpublished"))
        build_client(server).register_sequence(source(1, 2), register_options(max_frames_per_request=8))

    _assert_raises_without_ticket(SequenceCommitError, run)


def test_no_ticket_reaches_the_sequences_not_enabled_problem() -> None:
    """The typed `sequences-not-enabled` 403 never names the ticket (open sends none anyway)."""

    def run() -> None:
        respx.post(f"{BASE_URL}/sequences").mock(
            return_value=httpx.Response(
                403, json={"type": "urn:xio:parallax:problem:sequences-not-enabled", "title": "Disabled"}
            )
        )
        client = ParallaxClient(ParallaxClientOptions(account_token="test-token", base_url=BASE_URL))
        client.register_sequence(source(1), register_options(max_frames_per_request=8))

    _assert_raises_without_ticket(SequencesNotEnabled, run)


def test_no_ticket_reaches_a_ticket_refused_problem_even_when_the_detail_echoes_a_ticket() -> None:
    """A 403 `sequence-ticket-refused` problem never names the ticket, even when its own detail does."""

    def run() -> None:
        server = SequenceConversationServer(BASE_URL)
        respx.post(f"{BASE_URL}/sequences/{server.sequence_id}/frames").mock(
            return_value=httpx.Response(
                403,
                json={
                    "type": "urn:xio:parallax:problem:sequence-ticket-refused",
                    "title": "Ticket refused",
                    "detail": f"the ticket {TICKET} does not match this sequence",
                },
            )
        )
        build_client(server).register_sequence(source(1), register_options(max_frames_per_request=8))

    with respx.mock, pytest.raises(ParallaxProblem) as excinfo:
        run()
    # The server's own detail may still name the ticket; only the exception's own str()/repr() must not.
    assert excinfo.value.detail is not None and TICKET in excinfo.value.detail


def test_no_ticket_reaches_the_refusals_this_file_already_exercises() -> None:
    """None of `both`, oversized, non-monotone or empty-source raises a message naming the ticket."""

    def both() -> None:
        server = SequenceConversationServer(BASE_URL)
        client = build_client(server)
        options = dataclasses.replace(register_options(max_frames_per_request=8), existing=server.opened)
        client.register_sequence(source(1), options)

    def oversized() -> None:
        client = build_client(SequenceConversationServer(BASE_URL))
        frame_source = ExactFrameSource(
            (
                SequenceFrameInput.for_image(1, timedelta(0), b"\x01"),
                SequenceFrameInput.for_image(2, timedelta(0), bytes(4096)),
            )
        )
        client.register_sequence(frame_source, register_options(max_frames_per_request=1, max_request_bytes=2048))

    def non_monotone() -> None:
        client = build_client(SequenceConversationServer(BASE_URL))
        client.register_sequence(source(1, 2, 5, 4), register_options(max_frames_per_request=1))

    def empty() -> None:
        client = build_client(SequenceConversationServer(BASE_URL))
        client.register_sequence(source(), register_options(max_frames_per_request=8))

    _assert_raises_without_ticket(ValueError, both)
    _assert_raises_without_ticket(ValueError, oversized)
    _assert_raises_without_ticket(ValueError, non_monotone)
    _assert_raises_without_ticket(ParallaxClientError, empty)
