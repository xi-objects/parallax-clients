"""Comparison of an embedded C2PA store with a recovered record's manifests, by bytes (BLAKE3-256).

The record's `jumbf`-form manifests declare the BLAKE3-256 of the bytes the registrant attached; a store
found in an image matches when it hashes to one of them. `json`-form manifests are never compared.
`verification._record.normalize_record` is not reused: it refuses a record without a verification
block, which an unpublished record legitimately lacks, and this comparison needs only outcome and manifests.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import blake3

from .models import C2paComparison, C2paComparisonOutcome, EmbeddedC2paStore

_PUBLISHED = "published"
_JUMBF_FORM = "jumbf"


@dataclass(frozen=True, slots=True)
class _RecordManifest:
    """The fields of one record manifest the comparison reads."""

    kind: str
    form: str
    hash_hex: str | None


def _field(item: Any, key: str, attribute: str) -> Any:
    """Read `key` off a JSON dict or `attribute` off a generated model; UNSET reads as None."""
    value = item.get(key) if isinstance(item, Mapping) else getattr(item, attribute, None)
    return None if value is None or type(value).__name__ == "Unset" else value


def _manifests(record: Any) -> list[_RecordManifest]:
    """The record's manifests in one shape, from either a generated `PublishedRecordResponse` or a dict."""
    raw = _field(record, "manifests", "manifests") or []
    manifests: list[_RecordManifest] = []
    for item in raw:
        declared = _field(item, "hash", "hash_")
        manifests.append(
            _RecordManifest(
                kind=str(_field(item, "type", "type_")),
                form=str(_field(item, "form", "form")).lower(),
                hash_hex=str(declared).lower() if declared is not None else None,
            )
        )
    return manifests


def compare_with_record(store: EmbeddedC2paStore, record: Any) -> C2paComparison:
    """Compare `store` with a recovered record (a `PublishedRecordResponse` or its plain JSON dict)."""
    outcome = _field(record, "outcome", "outcome")
    if str(outcome) != _PUBLISHED:
        return C2paComparison(
            C2paComparisonOutcome.NOT_PUBLISHED, None, f"the record's outcome is {outcome!r}, not published"
        )
    candidates = [m for m in _manifests(record) if m.form == _JUMBF_FORM]
    if not candidates:
        return C2paComparison(
            C2paComparisonOutcome.ABSENT_FROM_RECORD, None, "the record carries no jumbf-form manifest"
        )
    digest = blake3.blake3(store.data).hexdigest()
    for manifest in candidates:
        if manifest.hash_hex == digest:
            return C2paComparison(
                C2paComparisonOutcome.MATCH, manifest.kind, f"BLAKE3-256 {digest} equals manifest {manifest.kind!r}"
            )
    kinds = ", ".join(repr(m.kind) for m in candidates)
    return C2paComparison(
        C2paComparisonOutcome.MISMATCH, None, f"BLAKE3-256 {digest} matches none of the jumbf manifests ({kinds})"
    )
