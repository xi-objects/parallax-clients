"""Tests for `frames.pure._reader`: refusal order, the deferred truncation clause, byte-exact reads."""

# PC-107: reader ordering and refusal tests

from __future__ import annotations

import os
import struct
from uuid import UUID

import blake3
from xio_parallax_client.frames.protocol import (
    PxBodyHeader,
    PxBucketContent,
    PxFrameAccepted,
    PxFrameRefusal,
    PxFrameRefused,
    PxHeadHeader,
)
from xio_parallax_client.frames.pure._encoder import encode
from xio_parallax_client.frames.pure._layout import (
    FORMAT_VERSION,
    FORMAT_VERSION_OFFSET,
    HASH_LENGTH,
    MAGIC,
    MINIMUM_FRAME_LENGTH,
)
from xio_parallax_client.frames.pure._reader import decode

_SEQUENCE_ID = UUID("12345678-1234-5678-1234-567812345678")


def _valid_body_frame() -> bytes:
    bucket = PxBucketContent("IMAG", b"payload-bytes")
    header = PxBodyHeader(_SEQUENCE_ID, 5, 4, 6, 1_000)
    return encode(header, [bucket]).frame


def test_body_round_trips() -> None:
    """A round trip through the pure encoder decodes back to the same header, buckets and hash."""
    encoded_frame = _valid_body_frame()
    result = decode(encoded_frame)
    assert isinstance(result, PxFrameAccepted)
    assert result.frame.header == PxBodyHeader(_SEQUENCE_ID, 5, 4, 6, 1_000)
    assert result.frame.buckets[0].data == b"payload-bytes"
    assert result.frame.frame_hash == blake3.blake3(encoded_frame[: len(encoded_frame) - HASH_LENGTH]).digest()


def test_head_frame_shortest_length() -> None:
    """A HEAD frame is exactly the minimum non-BODY length."""
    frame = encode(PxHeadHeader(_SEQUENCE_ID, 1), []).frame
    assert len(frame) == MINIMUM_FRAME_LENGTH
    result = decode(frame)
    assert isinstance(result, PxFrameAccepted)
    assert result.frame.buckets == ()


def test_truncated_below_the_minimum_length() -> None:
    """Anything shorter than 96 bytes is refused Truncated before any other rule runs."""
    result = decode(b"\x00" * 10)
    assert result == PxFrameRefused(PxFrameRefusal.TRUNCATED, result.detail)
    assert result.reason == PxFrameRefusal.TRUNCATED


def test_bad_magic() -> None:
    """A frame whose first four bytes are not PXFR is refused BadMagic."""
    frame = bytearray(_valid_body_frame())
    frame[0:4] = b"NOPE"
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.BAD_MAGIC


def test_unsupported_version() -> None:
    """A frame with a version this reader does not support is refused UnsupportedVersion."""
    frame = bytearray(_valid_body_frame())
    struct.pack_into("<H", frame, FORMAT_VERSION_OFFSET, FORMAT_VERSION + 1)
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.UNSUPPORTED_VERSION


def test_nothing_past_offset_6_is_read_before_the_version() -> None:
    """An unsupported version wins even when everything past offset 6 is unparseable garbage."""
    frame = MAGIC + struct.pack("<H", FORMAT_VERSION + 1) + os.urandom(90)
    assert len(frame) == MINIMUM_FRAME_LENGTH
    result = decode(frame)
    assert result == PxFrameRefused(PxFrameRefusal.UNSUPPORTED_VERSION, result.detail)


def test_truncated_by_declared_table_is_checked_after_version() -> None:
    """An unsupported version wins over a declared bucket table the input is too short to hold."""
    frame = bytearray(_valid_body_frame())
    struct.pack_into("<H", frame, FORMAT_VERSION_OFFSET, FORMAT_VERSION + 1)
    truncated = bytes(frame)[:100]  # shorter than this BODY frame's declared table needs
    result = decode(truncated)
    assert result.reason == PxFrameRefusal.UNSUPPORTED_VERSION


def test_declared_table_truncation_is_its_own_refusal() -> None:
    """A frame at the supported version but too short for its declared bucket table is refused Truncated."""
    frame = bytearray(_valid_body_frame())
    truncated = bytes(frame)[:100]
    result = decode(truncated)
    assert result.reason == PxFrameRefusal.TRUNCATED


def test_trailing_bytes_are_table_inconsistent() -> None:
    """Bytes appended past the frame the bucket table declares are refused BucketTableInconsistent."""
    frame = _valid_body_frame() + b"\x00" * 4
    result = decode(frame)
    assert result.reason == PxFrameRefusal.BUCKET_TABLE_INCONSISTENT


def test_bucket_hash_mismatch() -> None:
    """A bucket whose bytes were tampered with no longer hashes to its table row."""
    frame = bytearray(_valid_body_frame())
    frame[-HASH_LENGTH - 5] ^= 0xFF  # a byte inside the bucket's own data
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.BUCKET_HASH_MISMATCH


def test_frame_hash_mismatch() -> None:
    """A frame whose trailer no longer matches its own bytes is refused FrameHashMismatch."""
    frame = bytearray(_valid_body_frame())
    frame[-1] ^= 0xFF
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.FRAME_HASH_MISMATCH


def test_unknown_frame_type() -> None:
    """A frame-type byte outside 1-4 is refused UnknownFrameType."""
    frame = bytearray(_valid_body_frame())
    frame[6] = 9
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.UNKNOWN_FRAME_TYPE


def test_reserved_bits_set_in_presence_flags() -> None:
    """A reserved presence-flag bit (4-7) set to one is refused ReservedBitsSet."""
    frame = bytearray(_valid_body_frame())
    frame[7] |= 0x10
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.RESERVED_BITS_SET


def test_reserved_header_byte_set() -> None:
    """A reserved header byte (58-63) set to non-zero is refused ReservedBitsSet."""
    frame = bytearray(_valid_body_frame())
    frame[58] = 1
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.RESERVED_BITS_SET


def test_presence_flags_invalid_for_the_frame_type() -> None:
    """Presence flags that are not BODY's own legal set are refused PresenceFlagsInvalid."""
    frame = bytearray(_valid_body_frame())
    frame[7] = 0x01  # BODY needs 0x0B
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.PRESENCE_FLAGS_INVALID


def test_absent_field_not_zero() -> None:
    """A HEAD frame with a non-zero value in a slot its flags mark absent is refused AbsentFieldNotZero."""
    frame = bytearray(encode(PxHeadHeader(_SEQUENCE_ID, 1), []).frame)
    struct.pack_into("<q", frame, 32, 1)  # HEAD carries no prev slot
    result = decode(bytes(frame))
    assert result.reason == PxFrameRefusal.ABSENT_FIELD_NOT_ZERO
