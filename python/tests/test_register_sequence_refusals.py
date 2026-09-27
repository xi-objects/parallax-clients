"""What the register conversation refuses: the options, an oversized frame, a non-monotone id, an
empty source, and that no exception ever names the ticket.

Mirrors `RegisterSequenceRefusalTests` (.NET): a non-monotone id and an oversized frame are refused
naming the offending frame, before any request carries it; earlier batches may already have gone.
"""

# PC-114: what the register conversation refuses, sync

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta

import pytest
import respx
from xio_parallax_client import ParallaxClientError
from xio_parallax_client.frames.source import SequenceFrameInput

from .conftest import BASE_URL
from .sequence_server import SequenceConversationServer
from .test_register_sequence import build_client, register_options, source


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
