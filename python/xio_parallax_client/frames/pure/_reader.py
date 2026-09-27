"""Reads exactly one PX frame, checking the format's rules 1-15 in order, first failure winning.

Mirrors `Xio.Parallax.Common`'s `PxFrameReader` (`docs/px-frame.md`, "Reading a frame"). Every
count, offset and length is checked in 64-bit (native Python `int`) arithmetic before any slice of
the input is taken.
"""

# PC-107: decode(frame) -> PxFrameReadResult, rules 1-15 in order, the deferred truncation clause included

from __future__ import annotations

import struct
from uuid import UUID

import blake3

from ..protocol import (
    PxBodyHeader,
    PxBucket,
    PxBucketEntry,
    PxEndHeader,
    PxFrame,
    PxFrameAccepted,
    PxFrameHeader,
    PxFrameReadResult,
    PxFrameRefusal,
    PxFrameRefused,
    PxFrameType,
    PxGapHeader,
    PxGapRange,
    PxHeadHeader,
)
from ._layout import (
    BUCKET_COUNT_OFFSET,
    BUCKET_ENTRY_LENGTH,
    BUCKET_TABLE_OFFSET,
    BUCKET_TAG_LENGTH,
    ENTRY_HASH_OFFSET,
    ENTRY_LENGTH_OFFSET,
    ENTRY_OFFSET_OFFSET,
    ENTRY_TAG_OFFSET,
    FORMAT_VERSION,
    FORMAT_VERSION_OFFSET,
    FRAME_ID_OFFSET,
    FRAME_TYPE_OFFSET,
    HASH_LENGTH,
    HEADER_LENGTH,
    MAGIC,
    MINIMUM_FRAME_LENGTH,
    NEXT_OR_RANGE_TO_OFFSET,
    PRESENCE_FLAGS_OFFSET,
    PREV_OR_RANGE_FROM_OFFSET,
    RESERVED_OFFSET,
    SEQUENCE_ID_OFFSET,
    SOURCE_TIME_OFFSET,
)
from ._rules import BucketPlacement, HeaderFields, check_bucket_table, check_bucket_tags, check_header


def decode(frame: bytes) -> PxFrameReadResult:
    """PC-107: read one frame in the spec's check order; mirrors `PxFrameReader.DecodeAsync`."""
    parsed = _parse(frame)
    if isinstance(parsed, PxFrameRefused):
        return parsed

    header, entries = parsed
    for index, entry in enumerate(entries):
        bucket_data = frame[entry.offset : entry.offset + entry.length]
        if blake3.blake3(bucket_data).digest() != entry.hash:
            return _refused(PxFrameRefusal.BUCKET_HASH_MISMATCH, f"bucket {index} does not hash to its table row")

    hashed_length = len(frame) - HASH_LENGTH
    frame_hash = frame[hashed_length:]
    if blake3.blake3(frame[:hashed_length]).digest() != frame_hash:
        return _refused(PxFrameRefusal.FRAME_HASH_MISMATCH, "the frame does not hash to its trailer")

    buckets = tuple(PxBucket(entry, frame[entry.offset : entry.offset + entry.length]) for entry in entries)
    return PxFrameAccepted(PxFrame(header, buckets, frame_hash))


def _parse(frame: bytes) -> tuple[PxFrameHeader, tuple[PxBucketEntry, ...]] | PxFrameRefused:
    """Rules 1-13; nothing past offset 6 is read before the version is known."""
    if len(frame) < MINIMUM_FRAME_LENGTH:
        return _refused(PxFrameRefusal.TRUNCATED, f"{len(frame)} bytes is shorter than {MINIMUM_FRAME_LENGTH}")

    if frame[: len(MAGIC)] != MAGIC:
        return _refused(PxFrameRefusal.BAD_MAGIC, "the first bytes are not PXFR")

    (version,) = struct.unpack_from("<H", frame, FORMAT_VERSION_OFFSET)
    if version != FORMAT_VERSION:
        return _refused(PxFrameRefusal.UNSUPPORTED_VERSION, f"format version {version} is not {FORMAT_VERSION}")

    (bucket_count,) = struct.unpack_from("<H", frame, BUCKET_COUNT_OFFSET)
    declared_minimum = MINIMUM_FRAME_LENGTH + bucket_count * BUCKET_ENTRY_LENGTH
    if len(frame) < declared_minimum:
        return _refused(
            PxFrameRefusal.TRUNCATED, f"{len(frame)} bytes is shorter than the {declared_minimum} a {bucket_count}-bucket table needs"
        )

    fields = _read_fields(frame, bucket_count)
    tags = [_read_tag(frame, index) for index in range(bucket_count)]
    placements = [_read_placement(frame, index) for index in range(bucket_count)]
    violation = check_header(fields) or check_bucket_tags(tags) or check_bucket_table(placements, len(frame))
    if violation is not None:
        return _refused(violation.reason, violation.detail)

    entries = tuple(
        PxBucketEntry(tags[index], placements[index].offset, placements[index].length, _read_hash(frame, index))
        for index in range(bucket_count)
    )
    return _to_header(fields), entries


def _read_fields(frame: bytes, bucket_count: int) -> HeaderFields:
    """The header's raw fields, the sequence id in RFC 9562 order."""
    reserved = frame[RESERVED_OFFSET:HEADER_LENGTH]
    (frame_id,) = struct.unpack_from("<q", frame, FRAME_ID_OFFSET)
    (prev_or_from,) = struct.unpack_from("<q", frame, PREV_OR_RANGE_FROM_OFFSET)
    (next_or_to,) = struct.unpack_from("<q", frame, NEXT_OR_RANGE_TO_OFFSET)
    (source_time,) = struct.unpack_from("<q", frame, SOURCE_TIME_OFFSET)
    return HeaderFields(
        frame[FRAME_TYPE_OFFSET],
        frame[PRESENCE_FLAGS_OFFSET],
        reserved == bytes(len(reserved)),
        UUID(bytes=frame[SEQUENCE_ID_OFFSET : SEQUENCE_ID_OFFSET + 16]),
        frame_id,
        prev_or_from,
        next_or_to,
        source_time,
        bucket_count,
    )


def _row_start(index: int) -> int:
    """One bucket-table row's start offset."""
    return BUCKET_TABLE_OFFSET + index * BUCKET_ENTRY_LENGTH


def _read_tag(frame: bytes, index: int) -> str:
    """One row's tag, byte for character, so an out-of-range byte stays out of range."""
    start = _row_start(index) + ENTRY_TAG_OFFSET
    return "".join(chr(byte) for byte in frame[start : start + BUCKET_TAG_LENGTH])


def _read_placement(frame: bytes, index: int) -> BucketPlacement:
    """One row's offset and length, widened to native (64-bit) integers."""
    row = _row_start(index)
    (offset,) = struct.unpack_from("<I", frame, row + ENTRY_OFFSET_OFFSET)
    (length,) = struct.unpack_from("<I", frame, row + ENTRY_LENGTH_OFFSET)
    return BucketPlacement(offset, length)


def _read_hash(frame: bytes, index: int) -> bytes:
    """One row's stored bucket hash."""
    start = _row_start(index) + ENTRY_HASH_OFFSET
    return frame[start : start + HASH_LENGTH]


def _to_header(fields: HeaderFields) -> PxFrameHeader:
    """The header model of an accepted frame's fields."""
    frame_type = PxFrameType(fields.frame_type)
    if frame_type == PxFrameType.HEAD:
        return PxHeadHeader(fields.sequence_id, fields.frame_id)
    if frame_type == PxFrameType.BODY:
        return PxBodyHeader(
            fields.sequence_id, fields.frame_id, fields.prev_or_range_from, fields.next_or_range_to, fields.source_time_offset_microseconds
        )
    if frame_type == PxFrameType.END:
        return PxEndHeader(fields.sequence_id, fields.frame_id, fields.prev_or_range_from)
    return PxGapHeader(fields.sequence_id, fields.frame_id, PxGapRange(fields.prev_or_range_from, fields.next_or_range_to))


def _refused(reason: PxFrameRefusal, detail: str) -> PxFrameRefused:
    """The one refusal shape every rule check answers with."""
    return PxFrameRefused(reason, detail)
