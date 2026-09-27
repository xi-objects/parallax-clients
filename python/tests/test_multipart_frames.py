"""PC-112: sequence-frame multipart parts and the whole-body byte measurement they are sized by."""

from __future__ import annotations

import httpx
import respx
from xio_parallax_client.frames.protocol import PxFrameType
from xio_parallax_client.multipart import build_sequence_frame_parts, measure_multipart
from xio_parallax_client.sequences.encoding import EncodedFrame


def test_frame_parts_carry_name_file_name_and_content_type_in_order() -> None:
    frames = [
        EncodedFrame(5, PxFrameType.BODY, b"body-bytes", b"\x00" * 32),
        EncodedFrame(6, PxFrameType.END, b"end-bytes", b"\x00" * 32),
    ]

    parts = build_sequence_frame_parts(frames)

    assert parts == [
        ("5", ("5.px", b"body-bytes", "application/octet-stream")),
        ("6", ("6.px", b"end-bytes", "application/octet-stream")),
    ]


def test_measure_equals_the_body_httpx_sends() -> None:
    frames = [
        EncodedFrame(1, PxFrameType.BODY, b"abc", b"\x00" * 32),
        EncodedFrame(2, PxFrameType.END, b"defgh", b"\x00" * 32),
    ]
    parts = build_sequence_frame_parts(frames)
    expected = measure_multipart(parts)

    captured: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["length"] = int(request.headers["content-length"])
        return httpx.Response(200, json={})

    with respx.mock:
        respx.post("https://sequences.test/frames").mock(side_effect=handler)
        with httpx.Client() as client:
            client.post("https://sequences.test/frames", files=parts)

    assert captured["length"] == expected


def test_measure_grows_with_an_added_frame() -> None:
    one = [EncodedFrame(1, PxFrameType.BODY, b"x" * 50, b"\x00" * 32)]
    two = one + [EncodedFrame(2, PxFrameType.BODY, b"x" * 50, b"\x00" * 32)]

    assert measure_multipart(build_sequence_frame_parts(two)) > measure_multipart(build_sequence_frame_parts(one))


def test_measure_is_independent_of_call_order_for_the_same_parts() -> None:
    frames = [EncodedFrame(1, PxFrameType.BODY, b"same", b"\x00" * 32)]
    parts = build_sequence_frame_parts(frames)

    assert measure_multipart(parts) == measure_multipart(parts)
