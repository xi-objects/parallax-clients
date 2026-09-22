"""The shapes the C2PA layer reports: the carrier, the embedded store and its box walk, the comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class C2paCarrier(Enum):
    """The file format a C2PA manifest store was looked for in; UNSUPPORTED is a refusal to guess."""

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


@dataclass(frozen=True, slots=True)
class EmbeddedC2paStore:
    """The embedded manifest store's bytes, verbatim, and the boxes the walk could list in them."""

    data: bytes
    boxes: list[JumbfBoxSummary] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EmbeddedC2paResult:
    """What detection found: the carrier, the store (None when a supported carrier carries none) and why."""

    carrier: C2paCarrier
    store: EmbeddedC2paStore | None
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
