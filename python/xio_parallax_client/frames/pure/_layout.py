"""The PX Frame byte layout: magic, version, lengths, header and bucket-table offsets, declared once.

Mirrors `Xio.Parallax.Common`'s `PxFrameConstants` and `PxFrameLayout` (`docs/px-frame.md`, "The
header", "The bucket table"). Every other module in `pure/` derives its offsets from here; no
offset or length is written a second time.
"""

# PC-107: the format's fixed layout, declared once and derived everywhere else

from __future__ import annotations

from ..protocol import PxFrameType, PxPresenceFlags

#: The four-byte file signature every frame starts with.
MAGIC = b"PXFR"

#: The one format version this binding reads and writes.
FORMAT_VERSION = 1

#: The length of the fixed header, in bytes.
HEADER_LENGTH = 64

#: The length of one bucket-table row, in bytes.
BUCKET_ENTRY_LENGTH = 44

#: The length of a bucket tag, in ASCII bytes.
BUCKET_TAG_LENGTH = 4

#: The length of the sequence id, in bytes.
SEQUENCE_ID_LENGTH = 16

#: The BLAKE3-256 length of every bucket hash and of the frame-hash trailer.
HASH_LENGTH = 32

#: The length of a frame with no buckets: the shortest frame and every non-BODY frame.
MINIMUM_FRAME_LENGTH = HEADER_LENGTH + HASH_LENGTH

#: The lowest byte a bucket tag may carry.
MIN_BUCKET_TAG_BYTE = 0x21

#: The highest byte a bucket tag may carry.
MAX_BUCKET_TAG_BYTE = 0x7E

#: The largest value a bucket's declared length or offset may hold (u32).
MAX_U32 = 0xFFFFFFFF

#: The bounds of a signed 64-bit field (frame id, prev, next, source time offset).
MIN_I64 = -(2**63)
MAX_I64 = 2**63 - 1

#: The largest value the bucket count (u16) may hold.
MAX_U16 = 0xFFFF

# Header field offsets, in byte order.
MAGIC_OFFSET = 0
FORMAT_VERSION_OFFSET = 4
FRAME_TYPE_OFFSET = 6
PRESENCE_FLAGS_OFFSET = 7
SEQUENCE_ID_OFFSET = 8
FRAME_ID_OFFSET = 24
PREV_OR_RANGE_FROM_OFFSET = 32
NEXT_OR_RANGE_TO_OFFSET = 40
SOURCE_TIME_OFFSET = 48
BUCKET_COUNT_OFFSET = 56
RESERVED_OFFSET = 58

#: Where the bucket table starts: immediately after the header.
BUCKET_TABLE_OFFSET = HEADER_LENGTH

# Bucket-table row field offsets, relative to the row's own start.
ENTRY_TAG_OFFSET = 0
ENTRY_OFFSET_OFFSET = 4
ENTRY_LENGTH_OFFSET = 8
ENTRY_HASH_OFFSET = 12

#: The presence-flag bits 4-7, reserved and zero.
RESERVED_PRESENCE_FLAG_BITS = 0xF0

#: Each frame type's one legal set of presence-flag bits.
LEGAL_PRESENCE_FLAGS: dict[PxFrameType, PxPresenceFlags] = {
    PxFrameType.HEAD: PxPresenceFlags.NONE,
    PxFrameType.BODY: PxPresenceFlags.PREV | PxPresenceFlags.NEXT | PxPresenceFlags.SOURCE_TIME,
    PxFrameType.END: PxPresenceFlags.PREV,
    PxFrameType.GAP: PxPresenceFlags.RANGE,
}
