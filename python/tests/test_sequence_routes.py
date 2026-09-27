"""Open and the frames routes on `ParallaxClient`, mirroring `ParallaxClientSequencesOpenTests` and
`ParallaxClientSequencesFramesTests`: the two hand-written multipart routes, plus removing one frame.

The remaining seven route members (the generated request builders) are in
`test_sequence_routes_progress.py`, split out to keep this file under the project's 300-line cap.
"""

from __future__ import annotations

import base64
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from xio_parallax_client import ManifestForm, ManifestPart, ParallaxClient, ParallaxClientOptions, ParallaxProblem
from xio_parallax_client.frames.binding import default_frame_codec
from xio_parallax_client.frames.protocol import PxFrameType, PxHeadHeader
from xio_parallax_client.problems import SequencesNotEnabled
from xio_parallax_client.sequences import EncodedFrame, SequenceHandle, SequenceOpenRequest
from xio_parallax_client.sequences.wire import TICKET_HEADER

from .conftest import BASE_URL
from .sequence_server import multipart_parts


def _head_frame_base64(sequence_id: UUID, head_frame_id: int = 0) -> str:
    """A real base64 HEAD frame, encoded through the default codec, as open's own response carries it."""
    codec = default_frame_codec()
    encoded = codec.encode(PxHeadHeader(sequence_id, head_frame_id), ())
    return base64.b64encode(encoded.frame).decode("ascii")


@respx.mock
def test_open_sequence_sends_manifest_parts_and_expected_size_and_decodes_the_head_frame_id(
    options: ParallaxClientOptions,
) -> None:
    sequence_id = uuid4()
    route = respx.post(f"{BASE_URL}/sequences").mock(
        return_value=httpx.Response(
            201,
            json={
                "sequenceId": str(sequence_id),
                "ticket": "sequence-ticket-1",
                "headFrame": _head_frame_base64(sequence_id),
            },
        )
    )
    client = ParallaxClient(options)
    manifests = [ManifestPart("c2pa", ManifestForm.C2PA, b"\x01\x02\x03")]

    opened = client.open_sequence(SequenceOpenRequest(manifests, expected_size=12))

    assert opened.handle.sequence_id == sequence_id
    assert opened.handle.ticket == "sequence-ticket-1"
    assert opened.head_frame_id == 0

    parts = multipart_parts(route.calls.last.request)
    assert parts[0][0] == "manifest[c2pa]"
    assert parts[1] == ("expectedSize", b"12")


@respx.mock
def test_open_sequence_with_no_expected_size_sends_no_expected_size_part(options: ParallaxClientOptions) -> None:
    sequence_id = uuid4()
    route = respx.post(f"{BASE_URL}/sequences").mock(
        return_value=httpx.Response(
            201,
            json={"sequenceId": str(sequence_id), "ticket": "t", "headFrame": _head_frame_base64(sequence_id)},
        )
    )
    client = ParallaxClient(options)

    client.open_sequence(SequenceOpenRequest((), expected_size=None))

    assert multipart_parts(route.calls.last.request) == []


@respx.mock
def test_open_sequence_sends_no_ticket_header(options: ParallaxClientOptions) -> None:
    sequence_id = uuid4()
    route = respx.post(f"{BASE_URL}/sequences").mock(
        return_value=httpx.Response(
            201,
            json={"sequenceId": str(sequence_id), "ticket": "t", "headFrame": _head_frame_base64(sequence_id)},
        )
    )
    client = ParallaxClient(options)

    client.open_sequence(SequenceOpenRequest((), None))

    assert TICKET_HEADER not in route.calls.last.request.headers


@respx.mock
def test_open_sequence_when_the_accounts_gate_refuses_raises_the_typed_problem(options: ParallaxClientOptions) -> None:
    respx.post(f"{BASE_URL}/sequences").mock(
        return_value=httpx.Response(
            403,
            json={"type": "urn:xio:parallax:problem:sequences-not-enabled", "title": "Sequences disabled"},
        )
    )
    client = ParallaxClient(options)

    with pytest.raises(SequencesNotEnabled) as excinfo:
        client.open_sequence(SequenceOpenRequest((), None))
    assert excinfo.value.status == 403
    assert excinfo.value.slug == "sequences-not-enabled"


@respx.mock
def test_upload_sequence_frames_sends_one_octet_stream_file_part_per_frame_in_order(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-frames")
    frame1 = EncodedFrame(1, PxFrameType.BODY, b"body-one", b"\x00" * 32)
    frame2 = EncodedFrame(2, PxFrameType.BODY, b"body-two", b"\x00" * 32)
    route = respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/frames").mock(
        return_value=httpx.Response(
            201,
            json={"frames": [{"frameId": 1, "errata": False}, {"frameId": 2, "errata": False}], "verdict": None},
        )
    )
    client = ParallaxClient(options)

    response = client.upload_sequence_frames(handle, [frame1, frame2])

    assert len(response.frames) == 2
    assert response.verdict is None
    request = route.calls.last.request
    assert request.headers[TICKET_HEADER] == "sequence-ticket-frames"
    parts = multipart_parts(request)
    assert [name for name, _ in parts] == ["1", "2"]
    assert [body for _, body in parts] == [b"body-one", b"body-two"]


@respx.mock
def test_upload_sequence_frames_returns_the_verdict_when_the_batch_seals_the_sequence(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    frame = EncodedFrame(3, PxFrameType.END, b"end-bytes", b"\x00" * 32)
    respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/frames").mock(
        return_value=httpx.Response(
            201,
            json={
                "frames": [{"frameId": 3, "errata": False}],
                "verdict": {
                    "state": "sealed",
                    "framesReceived": 3,
                    "expectedSize": None,
                    "reach": 3,
                    "gaps": [],
                    "errata": [],
                    "connected": True,
                },
            },
        )
    )
    client = ParallaxClient(options)

    response = client.upload_sequence_frames(handle, [frame])

    assert response.verdict is not None
    assert response.verdict.state == "sealed"
    assert response.verdict.connected is True


def test_upload_sequence_frames_refuses_an_empty_list_before_sending_any_request(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    client = ParallaxClient(options)

    with respx.mock:
        route = respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/frames").mock(
            return_value=httpx.Response(201)
        )
        with pytest.raises(ValueError, match="at least one frame"):
            client.upload_sequence_frames(handle, [])
        assert route.call_count == 0


@respx.mock
def test_upload_sequence_frames_when_the_sequence_refuses_the_batch_raises_the_typed_problem(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    frame = EncodedFrame(1, PxFrameType.BODY, b"x", b"\x00" * 32)
    respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/frames").mock(
        return_value=httpx.Response(
            409, json={"type": "urn:xio:parallax:problem:sequence-not-open", "title": "Not open"}
        )
    )
    client = ParallaxClient(options)

    with pytest.raises(ParallaxProblem) as excinfo:
        client.upload_sequence_frames(handle, [frame])
    assert excinfo.value.status == 409
    assert excinfo.value.slug == "sequence-not-open"


@respx.mock
def test_remove_sequence_frame_deletes_the_given_frame_under_the_ticket_header(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-remove")
    route = respx.delete(f"{BASE_URL}/sequences/{handle.sequence_id}/frames/7").mock(
        return_value=httpx.Response(204)
    )
    client = ParallaxClient(options)

    assert client.remove_sequence_frame(handle, 7) is None
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-remove"
