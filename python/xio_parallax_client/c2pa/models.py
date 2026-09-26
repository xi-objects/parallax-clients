"""The shapes the C2PA layer reports: the carrier, the embedded JUMBF manifest stores, their boxes, the comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class C2paCarrier(Enum):
    """The file format an embedded manifest store was looked for in; UNSUPPORTED is a refusal to guess."""

    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    TIFF = "tiff"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class JumbfBoxSummary:
    """One JUMBF box as shown to a caller: its type, its description label (if any), nesting depth and size."""

    type: str
    label: str | None
    depth: int
    length: int


class EmbeddedC2paOutcome(Enum):
    """What detection could say about an image's embedded JUMBF manifest stores."""

    FOUND = "found"
    """At least one well-formed store, each classified `c2pa` or `jumbf`, one per kind."""
    ABSENT = "absent"
    """A supported carrier that holds no store."""
    MALFORMED = "malformed"
    """The carrier's slot holds bytes the JUMBF walk refused, or two stores of one kind."""
    UNSUPPORTED = "unsupported"
    """The carrier is not recognised, and nothing is said about whether it holds a store."""


@dataclass(frozen=True, slots=True)
class EmbeddedC2paStore:
    """One embedded JUMBF manifest store: its bytes verbatim, its kind (`c2pa` or `jumbf`) and its boxes."""

    data: bytes
    kind: str
    boxes: list[JumbfBoxSummary] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EmbeddedC2paResult:
    """What detection found: the carrier, the outcome, the stores in document order (FOUND only) and why."""

    carrier: C2paCarrier
    outcome: EmbeddedC2paOutcome
    stores: list[EmbeddedC2paStore]
    detail: str


class C2paComparisonOutcome(Enum):
    """How an embedded store relates to a recovered record's manifests."""

    MATCH = "match"
    MISMATCH = "mismatch"
    ABSENT_FROM_RECORD = "absentFromRecord"
    NOT_PUBLISHED = "notPublished"


@dataclass(frozen=True, slots=True)
class C2paComparison:
    """The comparison's outcome, the record manifest kind that matched (if any) and why."""

    outcome: C2paComparisonOutcome
    matched_kind: str | None
    detail: str
