"""The frame rules 4-13 the encoder and the reader share.

Mirrors `Xio.Parallax.Common`'s `PxFrameRules` (`docs/px-frame.md`, "Reading a frame"). Rules 1-3
(truncation, magic, version) and 14-15 (the hashes) are the reader's own business, since they need
bytes the encoder never produces malformed; rules 4-13 are shared because an encoder must refuse
input the reader would refuse.
"""

# PC-107: rules 4-13, checked in the format's own order, the first broken rule winning

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from ..protocol import PxFrameRefusal, PxFrameType, PxPresenceFlags
from ._layout import (
    BUCKET_ENTRY_LENGTH,
    BUCKET_TABLE_OFFSET,
    BUCKET_TAG_LENGTH,
    HASH_LENGTH,
    LEGAL_PRESENCE_FLAGS,
    MAX_BUCKET_TAG_BYTE,
    MAX_U32,
    MIN_BUCKET_TAG_BYTE,
    RESERVED_PRESENCE_FLAG_BITS,
)


@dataclass(frozen=True, slots=True)
class HeaderFields:
    """A frame's raw header fields, before they are read into a typed `PxFrameHeader`."""

    frame_type: int
    presence_flags: int
    reserved_bytes_clear: bool
    sequence_id: UUID
    frame_id: int
    prev_or_range_from: int
    next_or_range_to: int
    source_time_offset_microseconds: int
    bucket_count: int


@dataclass(frozen=True, slots=True)
class BucketPlacement:
    """One bucket's declared offset and length, read or computed in 64-bit arithmetic."""

    offset: int
    length: int


@dataclass(frozen=True, slots=True)
class RuleViolation:
    """The first rule a header, its tags or its bucket table broke, and a human-readable detail."""

    reason: PxFrameRefusal
    detail: str


def legal_presence_flags(frame_type: PxFrameType) -> PxPresenceFlags:
    """The one legal presence-flag set of a frame type."""
    return LEGAL_PRESENCE_FLAGS[frame_type]


def check_header(fields: HeaderFields) -> RuleViolation | None:
    """Check rules 4-11, in order, over a header's raw fields; `None` when none is broken."""
    try:
        frame_type = PxFrameType(fields.frame_type)
    except ValueError:
        return RuleViolation(PxFrameRefusal.UNKNOWN_FRAME_TYPE, f"frame type byte {fields.frame_type} names no frame type")

    if (fields.presence_flags & RESERVED_PRESENCE_FLAG_BITS) != 0 or not fields.reserved_bytes_clear:
        return RuleViolation(PxFrameRefusal.RESERVED_BITS_SET, "a reserved presence-flag bit or reserved header byte is set")

    legal = legal_presence_flags(frame_type)
    if fields.presence_flags != int(legal):
        return RuleViolation(
            PxFrameRefusal.PRESENCE_FLAGS_INVALID,
            f"presence flags 0x{fields.presence_flags:02X} are not {frame_type.name}'s 0x{int(legal):02X}",
        )

    absent_violation = _check_absent_slots(fields, legal)
    if absent_violation is not None:
        return absent_violation

    if fields.sequence_id.int == 0:
        return RuleViolation(PxFrameRefusal.NIL_SEQUENCE_ID, "the sequence id is nil")

    if not _is_link_order_valid(fields, frame_type):
        return RuleViolation(PxFrameRefusal.LINK_ORDER_INVALID, f"{frame_type.name} link fields break the type's ordering")

    if fields.source_time_offset_microseconds < 0:
        return RuleViolation(PxFrameRefusal.NEGATIVE_SOURCE_TIME, "the source time offset is negative")

    count_valid = (
        1 <= fields.bucket_count <= 0xFFFF if frame_type == PxFrameType.BODY else fields.bucket_count == 0
    )
    if not count_valid:
        return RuleViolation(PxFrameRefusal.BUCKET_COUNT_INVALID, f"{frame_type.name} cannot carry {fields.bucket_count} buckets")

    return None


def check_bucket_tags(tags: Sequence[str]) -> RuleViolation | None:
    """Check rule 12 over the bucket tags: four bytes in 0x21-0x7E, distinct within the frame."""
    seen: set[str] = set()
    for index, tag in enumerate(tags):
        if len(tag) != BUCKET_TAG_LENGTH or not _is_tag_text(tag):
            return RuleViolation(
                PxFrameRefusal.BUCKET_TAG_INVALID, f"bucket {index} tag is not {BUCKET_TAG_LENGTH} bytes in 0x21-0x7E"
            )
        if tag in seen:
            return RuleViolation(PxFrameRefusal.BUCKET_TAG_INVALID, f"bucket {index} repeats tag {tag}")
        seen.add(tag)

    return None


def check_bucket_table(placements: Sequence[BucketPlacement], frame_length: int) -> RuleViolation | None:
    """Check rule 13 over the bucket placements, in 64-bit arithmetic; `None` when none is broken."""
    buckets_end = frame_length - HASH_LENGTH
    expected_offset = BUCKET_TABLE_OFFSET + len(placements) * BUCKET_ENTRY_LENGTH
    for index, placement in enumerate(placements):
        if not (1 <= placement.length <= MAX_U32):
            return RuleViolation(
                PxFrameRefusal.BUCKET_TABLE_INCONSISTENT, f"bucket {index} length {placement.length} is outside 1-{MAX_U32}"
            )
        if placement.offset != expected_offset:
            return RuleViolation(
                PxFrameRefusal.BUCKET_TABLE_INCONSISTENT,
                f"bucket {index} offset {placement.offset} is not its contiguous position {expected_offset}",
            )
        expected_offset += placement.length
        if expected_offset > buckets_end:
            return RuleViolation(
                PxFrameRefusal.BUCKET_TABLE_INCONSISTENT, f"bucket {index} ends at {expected_offset}, past the trailer at {buckets_end}"
            )

    if expected_offset != buckets_end:
        return RuleViolation(
            PxFrameRefusal.BUCKET_TABLE_INCONSISTENT, f"the buckets end at {expected_offset}, not at the trailer at {buckets_end}"
        )

    return None


def _check_absent_slots(fields: HeaderFields, legal: PxPresenceFlags) -> RuleViolation | None:
    """Rule 7: every slot the flags mark absent holds zero."""
    first_slot_present = bool(legal & (PxPresenceFlags.PREV | PxPresenceFlags.RANGE))
    second_slot_present = bool(legal & (PxPresenceFlags.NEXT | PxPresenceFlags.RANGE))
    source_time_present = bool(legal & PxPresenceFlags.SOURCE_TIME)
    any_absent_set = (
        (not first_slot_present and fields.prev_or_range_from != 0)
        or (not second_slot_present and fields.next_or_range_to != 0)
        or (not source_time_present and fields.source_time_offset_microseconds != 0)
    )

    return (
        RuleViolation(PxFrameRefusal.ABSENT_FIELD_NOT_ZERO, "a slot the presence flags mark absent is not zero")
        if any_absent_set
        else None
    )


def _is_link_order_valid(fields: HeaderFields, frame_type: PxFrameType) -> bool:
    """Rule 9: BODY needs `prev < id < next`, END needs `prev < id`, GAP needs `from <= to`."""
    if frame_type == PxFrameType.BODY:
        return fields.prev_or_range_from < fields.frame_id < fields.next_or_range_to
    if frame_type == PxFrameType.END:
        return fields.prev_or_range_from < fields.frame_id
    if frame_type == PxFrameType.GAP:
        return fields.prev_or_range_from <= fields.next_or_range_to
    return True


def _is_tag_text(value: str) -> bool:
    """Every character of a tag falls within 0x21-0x7E."""
    return all(MIN_BUCKET_TAG_BYTE <= ord(character) <= MAX_BUCKET_TAG_BYTE for character in value)
