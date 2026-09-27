"""Encodes a header and its buckets as one PX frame, refusing input the reader would refuse.

Mirrors `Xio.Parallax.Common`'s `PxFrameEncoder` (`docs/px-frame.md`, "The header", "The bucket
table", "The buckets and the trailer", "Hashes"): write the header, the bucket table, the buckets
in order, then the frame-hash trailer.
"""

# PC-107: encode(header, buckets) -> EncodedPxFrame, refusing every rule 4-13 violation by name

from __future__ import annotations

import struct
from collections.abc import Sequence

import blake3

from ..protocol import (
    EncodedPxFrame,
    PxBodyHeader,
    PxBucketContent,
    PxEndHeader,
    PxFrameEncodeError,
    PxFrameHeader,
    PxFrameType,
    PxGapHeader,
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
    MAGIC,
    MAX_I64,
    MAX_U16,
    MIN_I64,
    NEXT_OR_RANGE_TO_OFFSET,
    PRESENCE_FLAGS_OFFSET,
    PREV_OR_RANGE_FROM_OFFSET,
    SEQUENCE_ID_LENGTH,
    SEQUENCE_ID_OFFSET,
    SOURCE_TIME_OFFSET,
)
from ._rules import (
    BucketPlacement,
    HeaderFields,
    check_bucket_table,
    check_bucket_tags,
    check_header,
    legal_presence_flags,
)


def encode(header: PxFrameHeader, buckets: Sequence[PxBucketContent]) -> EncodedPxFrame:
    """PC-107: encode one frame and its frame hash; mirrors `PxFrameEncoder.EncodeAsync`."""
    fields = _to_fields(header, len(buckets))
    _check_field_widths(fields)

    placements = _placements(buckets)
    frame_length = BUCKET_TABLE_OFFSET + len(buckets) * BUCKET_ENTRY_LENGTH + sum(len(b.data) for b in buckets) + HASH_LENGTH
    violation = (
        check_header(fields)
        or check_bucket_tags([bucket.tag for bucket in buckets])
        or check_bucket_table(placements, frame_length)
    )
    if violation is not None:
        raise PxFrameEncodeError(violation.reason, violation.detail)

    frame = bytearray(frame_length)
    _write_header(frame, fields)
    for index, (bucket, placement) in enumerate(zip(buckets, placements, strict=True)):
        row_start = BUCKET_TABLE_OFFSET + index * BUCKET_ENTRY_LENGTH
        bucket_hash = blake3.blake3(bucket.data).digest()
        _write_row(frame, row_start, bucket.tag, placement, bucket_hash)
        frame[placement.offset : placement.offset + placement.length] = bucket.data

    hashed_length = frame_length - HASH_LENGTH
    frame_hash = blake3.blake3(bytes(frame[:hashed_length])).digest()
    frame[hashed_length:] = frame_hash
    return EncodedPxFrame(bytes(frame), frame_hash)


def _to_fields(header: PxFrameHeader, bucket_count: int) -> HeaderFields:
    """PC-107: the header's raw fields; the type's one legal flag set, every absent slot zero."""
    if isinstance(header, PxHeadHeader):
        raw = (PxFrameType.HEAD, header.sequence_id, header.frame_id, 0, 0, 0)
    elif isinstance(header, PxBodyHeader):
        raw = (
            PxFrameType.BODY,
            header.sequence_id,
            header.frame_id,
            header.prev,
            header.next,
            header.source_time_offset_microseconds,
        )
    elif isinstance(header, PxEndHeader):
        raw = (PxFrameType.END, header.sequence_id, header.frame_id, header.prev, 0, 0)
    elif isinstance(header, PxGapHeader):
        raw = (PxFrameType.GAP, header.sequence_id, header.frame_id, header.range.range_from, header.range.range_to, 0)
    else:
        raise TypeError(f"{type(header).__name__} is no PX frame header")

    frame_type, sequence_id, frame_id, prev_or_from, next_or_to, source_time = raw
    presence_flags = int(legal_presence_flags(frame_type))
    return HeaderFields(int(frame_type), presence_flags, True, sequence_id, frame_id, prev_or_from, next_or_to, source_time, bucket_count)


def _check_field_widths(fields: HeaderFields) -> None:
    """A field that would not fit its wire width is a plain `ValueError`, never a silent wraparound."""
    for name, value in (
        ("frame_id", fields.frame_id),
        ("prev/range_from", fields.prev_or_range_from),
        ("next/range_to", fields.next_or_range_to),
        ("source_time_offset_microseconds", fields.source_time_offset_microseconds),
    ):
        if not (MIN_I64 <= value <= MAX_I64):
            raise ValueError(f"{name} does not fit a signed 64-bit field: {value}")
    if not (0 <= fields.bucket_count <= MAX_U16):
        raise ValueError(f"bucket count does not fit an unsigned 16-bit field: {fields.bucket_count}")


def _placements(buckets: Sequence[PxBucketContent]) -> list[BucketPlacement]:
    """Each bucket's contiguous offset and its declared length, computed before any byte is written."""
    placements: list[BucketPlacement] = []
    next_offset = BUCKET_TABLE_OFFSET + len(buckets) * BUCKET_ENTRY_LENGTH
    for bucket in buckets:
        placements.append(BucketPlacement(next_offset, len(bucket.data)))
        next_offset += len(bucket.data)
    return placements


def _write_header(frame: bytearray, fields: HeaderFields) -> None:
    """Magic, version, type, flags, sequence id in RFC 9562 order, ids, source time, count; reserved stays zero."""
    frame[0 : len(MAGIC)] = MAGIC
    struct.pack_into("<H", frame, FORMAT_VERSION_OFFSET, FORMAT_VERSION)
    frame[FRAME_TYPE_OFFSET] = fields.frame_type
    frame[PRESENCE_FLAGS_OFFSET] = fields.presence_flags
    # PC-107: rework - the declared sequence-id length, not a repeated literal
    frame[SEQUENCE_ID_OFFSET : SEQUENCE_ID_OFFSET + SEQUENCE_ID_LENGTH] = fields.sequence_id.bytes
    struct.pack_into("<q", frame, FRAME_ID_OFFSET, fields.frame_id)
    struct.pack_into("<q", frame, PREV_OR_RANGE_FROM_OFFSET, fields.prev_or_range_from)
    struct.pack_into("<q", frame, NEXT_OR_RANGE_TO_OFFSET, fields.next_or_range_to)
    struct.pack_into("<q", frame, SOURCE_TIME_OFFSET, fields.source_time_offset_microseconds)
    struct.pack_into("<H", frame, BUCKET_COUNT_OFFSET, fields.bucket_count)


def _write_row(frame: bytearray, row_start: int, tag: str, placement: BucketPlacement, bucket_hash: bytes) -> None:
    """One row's tag, offset, length and hash."""
    # PC-107: rework - the declared bucket-tag length, not a repeated literal
    frame[row_start + ENTRY_TAG_OFFSET : row_start + ENTRY_TAG_OFFSET + BUCKET_TAG_LENGTH] = tag.encode("ascii")
    struct.pack_into("<I", frame, row_start + ENTRY_OFFSET_OFFSET, placement.offset)
    struct.pack_into("<I", frame, row_start + ENTRY_LENGTH_OFFSET, placement.length)
    frame[row_start + ENTRY_HASH_OFFSET : row_start + ENTRY_HASH_OFFSET + HASH_LENGTH] = bucket_hash
