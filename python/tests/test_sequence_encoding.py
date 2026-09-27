"""PC-112: SequenceFrameEncoder against a fake PxFrameCodec, never the pure codec."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from xio_parallax_client.frames.protocol import (
    EncodedPxFrame,
    PxBodyHeader,
    PxBucketContent,
    PxFrame,
    PxFrameAccepted,
    PxFrameEncodeError,
    PxFrameRefusal,
    PxFrameRefused,
    PxFrameType,
    PxHeadHeader,
)
from xio_parallax_client.frames.source import SequenceFrameInput
from xio_parallax_client.sequences.encoding import EncodedFrame, SequenceFrameEncoder

_SEQUENCE_ID = UUID(int=1)


class FakeCodec:
    """Records every header and bucket set it is asked to encode; decodes canned frame bytes."""

    def __init__(self) -> None:
        self.encoded: list[tuple[object, tuple[PxBucketContent, ...]]] = []

    @property
    def format_version(self) -> int:
        return 1

    def encode(self, header, buckets):
        self.encoded.append((header, tuple(buckets)))
        return EncodedPxFrame(frame=f"FAKE:{header.frame_type.name}:{header.frame_id}".encode(), frame_hash=b"\x00" * 32)

    def decode(self, frame: bytes):
        if frame == b"HEAD":
            return PxFrameAccepted(PxFrame(PxHeadHeader(_SEQUENCE_ID, 7), (), b"\x00" * 32))
        if frame == b"BODY":
            return PxFrameAccepted(PxFrame(PxBodyHeader(_SEQUENCE_ID, 1, 0, 2, 0), (), b"\x00" * 32))
        return PxFrameRefused(PxFrameRefusal.BAD_MAGIC, "not a real frame")

    def build_chain(self, members):
        raise NotImplementedError

    def compute_sequence_hash(self, body_frame_hashes):
        raise NotImplementedError


def test_encode_body_records_header_and_buckets_and_returns_encoded_frame() -> None:
    codec = FakeCodec()
    encoder = SequenceFrameEncoder(codec)
    bucket = PxBucketContent("IMAG", b"image-bytes")
    frame_input = SequenceFrameInput(3, timedelta(microseconds=1500), (bucket,))

    result = encoder.encode_body(_SEQUENCE_ID, frame_input, prev=1, next_id=5)

    assert result == EncodedFrame(3, PxFrameType.BODY, b"FAKE:BODY:3", b"\x00" * 32)
    (header, buckets) = codec.encoded[0]
    assert header == PxBodyHeader(_SEQUENCE_ID, 3, 1, 5, 1500)
    assert buckets == (bucket,)


def test_encode_end_carries_no_buckets() -> None:
    codec = FakeCodec()
    encoder = SequenceFrameEncoder(codec)

    result = encoder.encode_end(_SEQUENCE_ID, frame_id=10, prev=9)

    assert result == EncodedFrame(10, PxFrameType.END, b"FAKE:END:10", b"\x00" * 32)
    (header, buckets) = codec.encoded[0]
    assert header.frame_id == 10
    assert header.prev == 9
    assert buckets == ()


# PC-112: rework - a codec refusal on encode_body is re-raised naming the frame id, not left bare
def test_encode_body_names_the_frame_id_when_the_codec_refuses_it() -> None:
    class RefusingCodec(FakeCodec):
        """A `FakeCodec` whose `encode` always refuses, as the real codec would mid-stream."""

        def encode(self, header, buckets):
            raise PxFrameEncodeError(PxFrameRefusal.BUCKET_TAG_INVALID, "bucket 0 tag is not 4 bytes in 0x21-0x7E")

    encoder = SequenceFrameEncoder(RefusingCodec())
    bucket = PxBucketContent("IMAG", b"image-bytes")
    frame_input = SequenceFrameInput(9, timedelta(0), (bucket,))

    with pytest.raises(ValueError, match="frame 9: "):
        encoder.encode_body(_SEQUENCE_ID, frame_input, prev=1, next_id=10)


def test_decode_head_frame_id_returns_the_head_id() -> None:
    encoder = SequenceFrameEncoder(FakeCodec())
    assert encoder.decode_head_frame_id(b"HEAD") == 7


def test_decode_head_frame_id_refuses_a_body_frame_naming_its_type() -> None:
    encoder = SequenceFrameEncoder(FakeCodec())
    with pytest.raises(ValueError, match="BODY is not a HEAD frame"):
        encoder.decode_head_frame_id(b"BODY")


def test_decode_head_frame_id_refuses_a_refused_decode_naming_the_reason() -> None:
    encoder = SequenceFrameEncoder(FakeCodec())
    with pytest.raises(ValueError, match="BadMagic is not a HEAD frame"):
        encoder.decode_head_frame_id(b"garbage")
