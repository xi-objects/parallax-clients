"""Tests for `frames.pure._encoder`: round trips, every reachable refusal rule, byte-exact layout.

`PurePxFrameCodec.encode` is exercised through the module function directly (`_encoder.encode`),
since the codec class is a thin composition PC-107 also owns.
"""

# PC-107: encoder round trips and refusals

from __future__ import annotations

import struct
from uuid import UUID, uuid4

import blake3
import pytest
from xio_parallax_client.frames.protocol import (
    PxBodyHeader,
    PxBucketContent,
    PxEndHeader,
    PxFrameAccepted,
    PxFrameEncodeError,
    PxFrameRefusal,
    PxGapHeader,
    PxGapRange,
    PxHeadHeader,
)
from xio_parallax_client.frames.pure._encoder import encode
from xio_parallax_client.frames.pure._layout import (
    BUCKET_COUNT_OFFSET,
    FORMAT_VERSION,
    FORMAT_VERSION_OFFSET,
    FRAME_ID_OFFSET,
    FRAME_TYPE_OFFSET,
    HEADER_LENGTH,
    MAGIC,
    MAX_U32,
    PRESENCE_FLAGS_OFFSET,
    SEQUENCE_ID_OFFSET,
)
from xio_parallax_client.frames.pure._reader import decode
from xio_parallax_client.frames.pure._rules import BucketPlacement, check_bucket_table

_SEQUENCE_ID = UUID("12345678-1234-5678-1234-567812345678")


def _body(frame_id: int = 5, prev: int = 4, next_: int = 6, offset: int = 1_000) -> PxBodyHeader:
    return PxBodyHeader(_SEQUENCE_ID, frame_id, prev, next_, offset)


def test_body_round_trips_one_bucket() -> None:
    """A BODY frame with one bucket encodes to the documented layout and hashes correctly."""
    bucket = PxBucketContent("IMAG", b"one-bucket-of-bytes")
    encoded = encode(_body(), [bucket])

    assert encoded.frame[: len(MAGIC)] == MAGIC
    (version,) = struct.unpack_from("<H", encoded.frame, FORMAT_VERSION_OFFSET)
    assert version == FORMAT_VERSION
    assert encoded.frame[FRAME_TYPE_OFFSET] == 2
    assert encoded.frame[PRESENCE_FLAGS_OFFSET] == 0x0B
    assert encoded.frame[SEQUENCE_ID_OFFSET : SEQUENCE_ID_OFFSET + 16] == _SEQUENCE_ID.bytes
    (frame_id,) = struct.unpack_from("<q", encoded.frame, FRAME_ID_OFFSET)
    assert frame_id == 5
    (bucket_count,) = struct.unpack_from("<H", encoded.frame, BUCKET_COUNT_OFFSET)
    assert bucket_count == 1

    table_row = encoded.frame[HEADER_LENGTH : HEADER_LENGTH + 44]
    assert table_row[0:4] == b"IMAG"
    (declared_offset,) = struct.unpack_from("<I", table_row, 4)
    (declared_length,) = struct.unpack_from("<I", table_row, 8)
    assert declared_offset == HEADER_LENGTH + 44
    assert declared_length == len(bucket.data)
    assert table_row[12:44] == blake3.blake3(bucket.data).digest()

    hashed_length = len(encoded.frame) - 32
    assert encoded.frame_hash == blake3.blake3(encoded.frame[:hashed_length]).digest()
    assert encoded.frame[hashed_length:] == encoded.frame_hash
    assert len(encoded.frame) == HEADER_LENGTH + 44 + len(bucket.data) + 32


def test_body_round_trips_two_buckets() -> None:
    """Two buckets lay out contiguously, in table order, each with its own hash."""
    buckets = [PxBucketContent("IMAG", b"first"), PxBucketContent("META", b"second-bucket")]
    encoded = encode(_body(), buckets)

    (bucket_count,) = struct.unpack_from("<H", encoded.frame, BUCKET_COUNT_OFFSET)
    assert bucket_count == 2

    first_row = encoded.frame[HEADER_LENGTH : HEADER_LENGTH + 44]
    second_row = encoded.frame[HEADER_LENGTH + 44 : HEADER_LENGTH + 88]
    (first_offset,) = struct.unpack_from("<I", first_row, 4)
    (first_length,) = struct.unpack_from("<I", first_row, 8)
    (second_offset,) = struct.unpack_from("<I", second_row, 4)
    assert first_offset == HEADER_LENGTH + 88
    assert first_length == len(buckets[0].data)
    assert second_offset == first_offset + first_length
    assert encoded.frame[first_offset : first_offset + first_length] == buckets[0].data
    assert encoded.frame[second_offset : second_offset + len(buckets[1].data)] == buckets[1].data


def test_head_round_trips() -> None:
    """A HEAD frame carries no link fields and no buckets."""
    encoded = encode(PxHeadHeader(_SEQUENCE_ID, 1), [])
    assert len(encoded.frame) == HEADER_LENGTH + 32
    assert encoded.frame[FRAME_TYPE_OFFSET] == 1
    assert encoded.frame[PRESENCE_FLAGS_OFFSET] == 0x00


def test_end_round_trips() -> None:
    """An END frame carries only prev."""
    encoded = encode(PxEndHeader(_SEQUENCE_ID, 9, 8), [])
    assert encoded.frame[FRAME_TYPE_OFFSET] == 3
    assert encoded.frame[PRESENCE_FLAGS_OFFSET] == 0x01
    (prev,) = struct.unpack_from("<q", encoded.frame, 32)
    assert prev == 8


def test_gap_round_trips() -> None:
    """A GAP frame's range occupies the prev/next slots under the RANGE flag."""
    encoded = encode(PxGapHeader(_SEQUENCE_ID, 100, PxGapRange(10, 20)), [])
    assert encoded.frame[FRAME_TYPE_OFFSET] == 4
    assert encoded.frame[PRESENCE_FLAGS_OFFSET] == 0x04
    (range_from,) = struct.unpack_from("<q", encoded.frame, 32)
    (range_to,) = struct.unpack_from("<q", encoded.frame, 40)
    assert (range_from, range_to) == (10, 20)


@pytest.mark.parametrize(
    ("header", "buckets", "reason"),
    [
        pytest.param(PxHeadHeader(UUID(int=0), 1), [], PxFrameRefusal.NIL_SEQUENCE_ID, id="nil-sequence-id"),
        pytest.param(_body(frame_id=5, prev=5), [PxBucketContent("IMAG", b"x")], PxFrameRefusal.LINK_ORDER_INVALID, id="prev-not-below-id"),
        pytest.param(PxEndHeader(_SEQUENCE_ID, 5, 5), [], PxFrameRefusal.LINK_ORDER_INVALID, id="end-prev-not-below-id"),
        pytest.param(PxGapHeader(_SEQUENCE_ID, 5, PxGapRange(10, 9)), [], PxFrameRefusal.LINK_ORDER_INVALID, id="gap-from-above-to"),
        pytest.param(
            PxBodyHeader(_SEQUENCE_ID, 5, 4, 6, -1),
            [PxBucketContent("IMAG", b"x")],
            PxFrameRefusal.NEGATIVE_SOURCE_TIME,
            id="negative-source-time",
        ),
        pytest.param(_body(), [], PxFrameRefusal.BUCKET_COUNT_INVALID, id="body-with-no-buckets"),
        pytest.param(PxHeadHeader(_SEQUENCE_ID, 1), [PxBucketContent("IMAG", b"x")], PxFrameRefusal.BUCKET_COUNT_INVALID, id="head-with-a-bucket"),
        pytest.param(_body(), [PxBucketContent(" BAD", b"x")], PxFrameRefusal.BUCKET_TAG_INVALID, id="tag-out-of-range"),
        pytest.param(
            _body(),
            [PxBucketContent("IMAG", b"x"), PxBucketContent("IMAG", b"y")],
            PxFrameRefusal.BUCKET_TAG_INVALID,
            id="duplicate-tag",
        ),
        pytest.param(_body(), [PxBucketContent("IMAG", b"")], PxFrameRefusal.BUCKET_TABLE_INCONSISTENT, id="empty-bucket"),
    ],
)
def test_encode_refuses_each_rule_with_its_reason(
    header: PxHeadHeader | PxBodyHeader | PxEndHeader | PxGapHeader, buckets: list[PxBucketContent], reason: PxFrameRefusal
) -> None:
    """Each rule an encoder can meet is refused with its own `PxFrameRefusal` reason."""
    with pytest.raises(PxFrameEncodeError) as excinfo:
        encode(header, buckets)
    assert excinfo.value.reason == reason
    assert str(reason.value) in str(excinfo.value)


@pytest.mark.parametrize(
    ("header", "buckets", "field"),
    [
        pytest.param(PxBodyHeader(_SEQUENCE_ID, 2**63, 4, 6, 0), [PxBucketContent("IMAG", b"x")], "frame_id", id="frame-id-overflow"),
        pytest.param(PxBodyHeader(_SEQUENCE_ID, 5, -(2**63) - 1, 6, 0), [PxBucketContent("IMAG", b"x")], "prev", id="prev-overflow"),
    ],
)
def test_encode_refuses_a_64_bit_overflow_naming_the_field(
    header: PxBodyHeader, buckets: list[PxBucketContent], field: str
) -> None:
    """A value that cannot fit a signed 64-bit field is refused before any slice of the frame is built."""
    with pytest.raises(ValueError, match=field) as excinfo:
        encode(header, buckets)
    assert "64-bit" in str(excinfo.value)


# PC-107: rework - the bucket-table check refuses an offset the wire's u32 field cannot hold, not only its length
def test_check_bucket_table_refuses_an_out_of_range_offset() -> None:
    """A bucket placement whose offset exceeds u32 is refused BUCKET_TABLE_INCONSISTENT, never a struct.error."""
    placement = BucketPlacement(offset=MAX_U32 + 1, length=1)
    violation = check_bucket_table([placement], frame_length=MAX_U32 + 100)
    assert violation is not None
    assert violation.reason == PxFrameRefusal.BUCKET_TABLE_INCONSISTENT
    assert str(MAX_U32 + 1) in violation.detail


def test_encoded_frame_re_decodes_byte_identical() -> None:
    """A round trip through the decoder answers the same header and bucket bytes the encoder wrote."""
    bucket = PxBucketContent("IMAG", b"round-trip-bytes")
    header = _body()
    encoded = encode(header, [bucket])

    result = decode(encoded.frame)
    assert isinstance(result, PxFrameAccepted)
    assert result.frame.header == header
    assert result.frame.frame_hash == encoded.frame_hash
    assert len(result.frame.buckets) == 1
    assert result.frame.buckets[0].data == bucket.data
    assert result.frame.buckets[0].entry.tag == "IMAG"

    re_encoded = encode(result.frame.header, [PxBucketContent(b.entry.tag, b.data) for b in result.frame.buckets])
    assert re_encoded.frame == encoded.frame


def test_distinct_sequence_ids_do_not_collide() -> None:
    """Two frames of the same content but different sequence ids encode to different bytes."""
    bucket = PxBucketContent("IMAG", b"x")
    a = encode(_body(), [bucket])
    b = encode(PxBodyHeader(uuid4(), 5, 4, 6, 1_000), [bucket])
    assert a.frame != b.frame
