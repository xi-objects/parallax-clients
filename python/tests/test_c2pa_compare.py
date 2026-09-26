"""Comparison of an embedded store with a recovered record, and the round trip through the real fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import blake3
import pytest
from xio_parallax_client import (
    C2paCarrier,
    C2paComparisonOutcome,
    EmbeddedC2paStore,
    compare_with_record,
    detect_embedded_c2pa,
)
from xio_parallax_client.generated.models.published_record_response import PublishedRecordResponse

from .carriers import synthetic_store

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "record"

_requires_fixture = pytest.mark.skipif(
    not _FIXTURE_DIR.is_dir(),
    reason="fixtures/record is not present: a local capture, not part of the repository",
)


def _record(manifests: list[dict[str, Any]], outcome: str = "published") -> dict[str, Any]:
    """A record dict in the shape `GET /records/{hash}` answers (only outcome and manifests are read)."""
    return {"originalImageHash": "00" * 32, "outcome": outcome, "manifests": manifests, "verification": None}


def _manifest(kind: str, form: str, data: bytes) -> dict[str, Any]:
    """One record manifest whose declared hash is the BLAKE3-256 of `data`."""
    return {"type": kind, "form": form, "payload": "", "hash": blake3.blake3(data).hexdigest(), "signature": ""}


def _fixture() -> tuple[bytes, dict[str, Any]]:
    """The live-record fixture: the attached `c2pa` manifest bytes and the record that declares their hash."""
    stored = (_FIXTURE_DIR / "manifest.jumbf").read_bytes()
    record = json.loads((_FIXTURE_DIR / "record.json").read_text(encoding="utf-8"))
    return stored, record


def test_match_when_a_jumbf_manifest_hashes_to_the_store() -> None:
    store = EmbeddedC2paStore(data=synthetic_store())
    record = _record([_manifest("xi-manifest", "json", b"{}"), _manifest("c2pa", "jumbf", store.data)])
    comparison = compare_with_record(store, record)
    assert comparison.outcome is C2paComparisonOutcome.MATCH
    assert comparison.matched_kind == "c2pa"


def test_mismatch_when_no_jumbf_manifest_hashes_to_the_store() -> None:
    store = EmbeddedC2paStore(data=synthetic_store())
    comparison = compare_with_record(store, _record([_manifest("c2pa", "jumbf", b"other bytes")]))
    assert comparison.outcome is C2paComparisonOutcome.MISMATCH
    assert comparison.matched_kind is None


def test_absent_when_only_a_json_manifest_hashes_equal() -> None:
    store = EmbeddedC2paStore(data=synthetic_store())
    comparison = compare_with_record(store, _record([_manifest("c2pa", "json", store.data)]))
    assert comparison.outcome is C2paComparisonOutcome.ABSENT_FROM_RECORD
    assert comparison.matched_kind is None


def test_not_published_when_the_outcome_is_not_published() -> None:
    store = EmbeddedC2paStore(data=synthetic_store())
    record = _record([_manifest("c2pa", "jumbf", store.data)], outcome="takenDown")
    comparison = compare_with_record(store, record)
    assert comparison.outcome is C2paComparisonOutcome.NOT_PUBLISHED


@_requires_fixture
def test_generated_model_record_compares_like_its_dict() -> None:
    stored, record = _fixture()
    comparison = compare_with_record(EmbeddedC2paStore(data=stored), PublishedRecordResponse.from_dict(record))
    assert comparison.outcome is C2paComparisonOutcome.MATCH
    assert comparison.matched_kind == "c2pa"


@_requires_fixture
def test_fixture_round_trip_finds_and_matches_the_store_embedded_in_the_image() -> None:
    """The genuine finder flow: `image.png` itself carries the store, in its `caBX` chunk."""
    stored, record = _fixture()
    image = (_FIXTURE_DIR / "image.png").read_bytes()
    result = detect_embedded_c2pa(image)
    assert result.carrier is C2paCarrier.PNG
    assert result.store is not None
    assert result.store.data == stored
    shown = [(b.type, b.label) for b in result.store.boxes]
    assert shown == [("jumb", "c2pa"), ("jumd", "c2pa"), ("json", None)]
    comparison = compare_with_record(result.store, record)
    assert comparison.outcome is C2paComparisonOutcome.MATCH
    assert comparison.matched_kind == "c2pa"


@_requires_fixture
def test_fixture_round_trip_a_flipped_byte_mismatches() -> None:
    stored, record = _fixture()
    flipped = bytearray(stored)
    flipped[-1] ^= 0xFF
    comparison = compare_with_record(EmbeddedC2paStore(data=bytes(flipped)), record)
    assert comparison.outcome is C2paComparisonOutcome.MISMATCH
