"""The PX Frame seam: the one protocol the client and the sequence conversation depend on.

`PxFrameCodec` is the whole of what this package asks of a PX Frame implementation: encode a
frame, decode one, build a chain from members, and compute a sequence hash. The frozen types
below are the language of that protocol, mirroring `Xio.Parallax.Common` (`docs/px-frame.md` in
`xio_parallax_common`, the format's design of record). Nothing here implements the format; a
binding does, and a binding is swapped without any change to the code that calls it.
"""

# PC-107: the seam's contract; bindings implement it, nothing here implements the format

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from typing import ClassVar, Protocol, TypeAlias, runtime_checkable
from uuid import UUID

#: The one bucket tag the format itself declares: the image a BODY frame carries.
IMAGE_BUCKET_TAG = "IMAG"


class PxFrameType(IntEnum):
    """The four frame types, valued as the header's frame-type byte; each name is the vectors' `type`."""

    HEAD = 1
    BODY = 2
    END = 3
    GAP = 4


class PxPresenceFlags(IntFlag):
    """The header's presence-flag bits; each frame type has exactly one legal set of them."""

    NONE = 0x00
    PREV = 0x01
    NEXT = 0x02
    RANGE = 0x04
    SOURCE_TIME = 0x08


class PxFrameRefusal(Enum):
    """Why a reader refused a frame: declaration order is check order; values are the vectors' `reason` names."""

    TRUNCATED = "Truncated"
    BAD_MAGIC = "BadMagic"
    UNSUPPORTED_VERSION = "UnsupportedVersion"
    UNKNOWN_FRAME_TYPE = "UnknownFrameType"
    RESERVED_BITS_SET = "ReservedBitsSet"
    PRESENCE_FLAGS_INVALID = "PresenceFlagsInvalid"
    ABSENT_FIELD_NOT_ZERO = "AbsentFieldNotZero"
    NIL_SEQUENCE_ID = "NilSequenceId"
    LINK_ORDER_INVALID = "LinkOrderInvalid"
    NEGATIVE_SOURCE_TIME = "NegativeSourceTime"
    BUCKET_COUNT_INVALID = "BucketCountInvalid"
    BUCKET_TAG_INVALID = "BucketTagInvalid"
    BUCKET_TABLE_INCONSISTENT = "BucketTableInconsistent"
    BUCKET_HASH_MISMATCH = "BucketHashMismatch"
    FRAME_HASH_MISMATCH = "FrameHashMismatch"


class PxChainRefusal(Enum):
    """Why building a chain was refused: declaration order is check order; values are the format's names."""

    GAP_FRAME_NOT_MEMBER = "GapFrameNotMember"
    HEAD_MISSING = "HeadMissing"
    HEAD_DUPLICATED = "HeadDuplicated"
    END_DUPLICATED = "EndDuplicated"
    SEQUENCE_MISMATCH = "SequenceMismatch"
    DUPLICATE_FRAME_ID = "DuplicateFrameId"
    BELOW_HEAD = "BelowHead"
    BEYOND_END = "BeyondEnd"
    LINK_CLAIMED_TWICE = "LinkClaimedTwice"
    LINK_DISAGREEMENT = "LinkDisagreement"
    LINK_CROSSING = "LinkCrossing"


@dataclass(frozen=True, slots=True)
class PxGapRange:
    """An inclusive range of frame ids, `range_from` to `range_to`: the ids a fill may take."""

    range_from: int
    range_to: int


@dataclass(frozen=True, slots=True)
class PxHeadHeader:
    """A HEAD frame's header: it opens a sequence and carries no link fields."""

    frame_type: ClassVar[PxFrameType] = PxFrameType.HEAD
    sequence_id: UUID
    frame_id: int


@dataclass(frozen=True, slots=True)
class PxBodyHeader:
    """A BODY frame's header: its prev and next links and its source time offset in microseconds."""

    frame_type: ClassVar[PxFrameType] = PxFrameType.BODY
    sequence_id: UUID
    frame_id: int
    prev: int
    next: int
    source_time_offset_microseconds: int


@dataclass(frozen=True, slots=True)
class PxEndHeader:
    """An END frame's header: it closes a sequence and names its prev link."""

    frame_type: ClassVar[PxFrameType] = PxFrameType.END
    sequence_id: UUID
    frame_id: int
    prev: int


@dataclass(frozen=True, slots=True)
class PxGapHeader:
    """A GAP frame's header: it names an inclusive range of missing frame ids."""

    frame_type: ClassVar[PxFrameType] = PxFrameType.GAP
    sequence_id: UUID
    frame_id: int
    range: PxGapRange


#: A frame's header, one type per frame type.
PxFrameHeader: TypeAlias = PxHeadHeader | PxBodyHeader | PxEndHeader | PxGapHeader


@dataclass(frozen=True, slots=True)
class PxBucketContent:
    """A bucket to encode: its four-character ASCII tag and its bytes."""

    tag: str
    data: bytes


@dataclass(frozen=True, slots=True)
class PxBucketEntry:
    """One bucket-table row as read: tag, offset from the frame's first byte, length, BLAKE3-256 hash."""

    tag: str
    offset: int
    length: int
    hash: bytes


@dataclass(frozen=True, slots=True)
class PxBucket:
    """A decoded bucket: its table row and its bytes."""

    entry: PxBucketEntry
    data: bytes


@dataclass(frozen=True, slots=True)
class EncodedPxFrame:
    """An encoded frame's bytes and its frame hash, the 32-byte trailer the bytes end with."""

    frame: bytes
    frame_hash: bytes


@dataclass(frozen=True, slots=True)
class PxFrame:
    """A decoded frame: its header, its buckets in table order, and its frame hash."""

    header: PxFrameHeader
    buckets: tuple[PxBucket, ...]
    frame_hash: bytes


@dataclass(frozen=True, slots=True)
class PxFrameAccepted:
    """A frame the reader accepted, and what it read."""

    frame: PxFrame


@dataclass(frozen=True, slots=True)
class PxFrameRefused:
    """A frame the reader refused: the first rule it broke, in check order, and a detail."""

    reason: PxFrameRefusal
    detail: str


#: What reading a frame answers.
PxFrameReadResult: TypeAlias = PxFrameAccepted | PxFrameRefused


class PxFrameEncodeError(ValueError):
    """Raised by `PxFrameCodec.encode` for input the reader would refuse.

    Carries the refusal the frame would have met; the message starts with the reason's name.
    """

    def __init__(self, reason: PxFrameRefusal, detail: str) -> None:
        super().__init__(f"{reason.value}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class PxChainMember:
    """One chain member: a frame's header and its frame hash, with no bucket bytes."""

    header: PxFrameHeader
    frame_hash: bytes


@dataclass(frozen=True, slots=True)
class PxChain:
    """A built chain: walk from HEAD, reach, gaps, END present (sealed), walk arrives at END (connected)."""

    sequence_id: UUID
    walk: tuple[PxChainMember, ...]
    reach: int
    gaps: tuple[PxGapRange, ...]
    is_sealed: bool
    is_connected: bool

    @property
    def body_frame_hashes_in_walk_order(self) -> tuple[bytes, ...]:
        """The walk's BODY frame hashes, in walk order, HEAD and END excluded: the sequence hash's input."""
        return tuple(member.frame_hash for member in self.walk if isinstance(member.header, PxBodyHeader))


@dataclass(frozen=True, slots=True)
class PxChainBuilt:
    """A member set the builder accepted, and the chain it forms."""

    chain: PxChain


@dataclass(frozen=True, slots=True)
class PxChainRefused:
    """A member set the builder refused: the first rule broken, the offending member's frame id, a detail."""

    reason: PxChainRefusal
    frame_id: int
    detail: str


#: What building a chain answers.
PxChainBuildResult: TypeAlias = PxChainBuilt | PxChainRefused


@runtime_checkable
class PxFrameCodec(Protocol):
    """The PX Frame format as the client needs it: the one seam every binding implements.

    A conforming binding answers every vector of `xio_parallax_common`'s `vectors/` exactly as that
    repository's own tests expect: accepted frames decode to their sidecars and re-encode byte for
    byte, refused frames answer their sidecar's reason, and chains build to their `chain.json`.
    Every method is synchronous and keeps no state between calls.
    """

    @property
    def format_version(self) -> int:
        """The one format version this binding reads and writes."""
        ...

    def encode(self, header: PxFrameHeader, buckets: Sequence[PxBucketContent]) -> EncodedPxFrame:
        """Encode one frame and its frame hash; raise `PxFrameEncodeError` for input the reader would refuse."""
        ...

    def decode(self, frame: bytes) -> PxFrameReadResult:
        """Read exactly one frame, checking the format's rules in order; answer it or the first rule it breaks."""
        ...

    def build_chain(self, members: Collection[PxChainMember]) -> PxChainBuildResult:
        """Build one chain from members in any order, or answer the first chain rule broken.

        Raises `ValueError` for an empty member set, or for a member whose own links break its
        frame type's order.
        """
        ...

    def compute_sequence_hash(self, body_frame_hashes: Sequence[bytes]) -> bytes:
        """BLAKE3-256 over the BODY frame hashes concatenated in the order given.

        Raises `ValueError` for an empty list, or for a hash that is not 32 bytes.
        """
        ...
