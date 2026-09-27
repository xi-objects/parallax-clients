"""The async mirror of `test_sequence_routes.py`: the sequence route members on `AsyncParallaxClient`.

Covers the same parity points as the sync suite (ticket header, open's no-ticket / no-manifest
shapes, the typed 403, the empty-upload and out-of-range refusals, and a 409 on frames), without
repeating every route the sync suite already proves member for member.
"""

from __future__ import annotations

import base64
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from xio_parallax_client import AsyncParallaxClient, ManifestForm, ManifestPart, ParallaxClientOptions, ParallaxProblem
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
async def test_open_sequence_sends_manifest_parts_and_decodes_the_head_frame_id(
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
    client = AsyncParallaxClient(options)
    manifests = [ManifestPart("c2pa", ManifestForm.C2PA, b"\x01\x02\x03")]

    opened = await client.open_sequence(SequenceOpenRequest(manifests, expected_size=12))

    assert opened.handle.sequence_id == sequence_id
    assert opened.head_frame_id == 0
    parts = multipart_parts(route.calls.last.request)
    assert parts[0][0] == "manifest[c2pa]"
    assert parts[1] == ("expectedSize", b"12")
    assert TICKET_HEADER not in route.calls.last.request.headers


@respx.mock
async def test_open_sequence_when_the_accounts_gate_refuses_raises_the_typed_problem(
    options: ParallaxClientOptions,
) -> None:
    respx.post(f"{BASE_URL}/sequences").mock(
        return_value=httpx.Response(
            403, json={"type": "urn:xio:parallax:problem:sequences-not-enabled", "title": "Sequences disabled"}
        )
    )
    client = AsyncParallaxClient(options)

    with pytest.raises(SequencesNotEnabled) as excinfo:
        await client.open_sequence(SequenceOpenRequest((), None))
    assert excinfo.value.status == 403
    assert excinfo.value.slug == "sequences-not-enabled"


@respx.mock
async def test_upload_sequence_frames_sends_one_octet_stream_file_part_per_frame_under_the_ticket_header(
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
    client = AsyncParallaxClient(options)

    response = await client.upload_sequence_frames(handle, [frame1, frame2])

    assert len(response.frames) == 2
    request = route.calls.last.request
    assert request.headers[TICKET_HEADER] == "sequence-ticket-frames"
    parts = multipart_parts(request)
    assert [name for name, _ in parts] == ["1", "2"]


async def test_upload_sequence_frames_refuses_an_empty_list_before_sending_any_request(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    client = AsyncParallaxClient(options)

    with respx.mock:
        route = respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/frames").mock(
            return_value=httpx.Response(201)
        )
        with pytest.raises(ValueError, match="at least one frame"):
            await client.upload_sequence_frames(handle, [])
        assert route.call_count == 0


@respx.mock
async def test_upload_sequence_frames_when_the_sequence_refuses_the_batch_raises_the_typed_problem(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    frame = EncodedFrame(1, PxFrameType.BODY, b"x", b"\x00" * 32)
    respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/frames").mock(
        return_value=httpx.Response(
            409, json={"type": "urn:xio:parallax:problem:sequence-not-open", "title": "Not open"}
        )
    )
    client = AsyncParallaxClient(options)

    with pytest.raises(ParallaxProblem) as excinfo:
        await client.upload_sequence_frames(handle, [frame])
    assert excinfo.value.status == 409
    assert excinfo.value.slug == "sequence-not-open"


@pytest.mark.parametrize("expected_size", [0, -1, 2**31])
async def test_amend_sequence_expected_size_refuses_out_of_range_before_sending_any_request(
    options: ParallaxClientOptions, expected_size: int
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    client = AsyncParallaxClient(options)

    with respx.mock:
        route = respx.put(f"{BASE_URL}/sequences/{handle.sequence_id}/expected-size").mock(
            return_value=httpx.Response(204)
        )
        with pytest.raises(ValueError, match="expected_size"):
            await client.amend_sequence_expected_size(handle, expected_size)
        assert route.call_count == 0


@respx.mock
async def test_commit_sequence_sends_post_commit_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-commit")
    route = respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/commit").mock(
        return_value=httpx.Response(
            200,
            json={"outcome": "registered", "sequenceHash": "abc123", "sequenceRecordPublished": True, "frames": []},
        )
    )
    client = AsyncParallaxClient(options)

    response = await client.commit_sequence(handle)

    assert response.outcome == "registered"
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-commit"


@respx.mock
async def test_abandon_sequence_sends_delete_sequence_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-abandon")
    route = respx.delete(f"{BASE_URL}/sequences/{handle.sequence_id}").mock(
        return_value=httpx.Response(
            200, json={"sequenceId": str(handle.sequence_id), "state": "abandoned", "packetsPurged": 4}
        )
    )
    client = AsyncParallaxClient(options)

    response = await client.abandon_sequence(handle)

    assert response.state == "abandoned"
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-abandon"
