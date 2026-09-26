"""Conformance tests: the verifier against one real record captured from the live API (see `fixtures/README.md`).

`fixtures/record/` holds `record.json` (`GET /records/{originalImageHash}`, byte for byte), the image it was
registered with, the dev CA root its chain terminates at, and that Orbital's anonymous `GET /info`. Every
performed check on this record must pass; these tests also probe the two ways it can be made to fail.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.x509.oid import NameOID
from xio_parallax_client.verification import AttributionVerifier, CheckOutcome, TrustRoots

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "record"
_LOOKUP_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "lookup"
_LEGACY_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "record-legacy"

pytestmark = pytest.mark.skipif(
    not _FIXTURE_DIR.is_dir() or not _LOOKUP_FIXTURE_DIR.is_dir() or not _LEGACY_FIXTURE_DIR.is_dir(),
    reason="fixtures/record, fixtures/lookup or fixtures/record-legacy is not present: a local capture, not part of the repository",
)

_EXPECTED_PASSED = (
    "originalImageHash",
    "contentHash",
    "manifestHash:c2pa",
    "manifestSignature:c2pa",
    "manifestSignature:xi-manifest",
    "collectionSignature",
    "imageSignature",
    "leafKeyMatchesPublicKey",
    "certificateChain",
)


def _record() -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / "record.json").read_text(encoding="utf-8"))


def _image_bytes() -> bytes:
    return (_FIXTURE_DIR / "image.png").read_bytes()


def _root_pem_bytes() -> bytes:
    return (_FIXTURE_DIR / "root.pem").read_bytes()


def _orbital_info_bytes() -> bytes:
    return (_FIXTURE_DIR / "orbital-info.json").read_bytes()


def _wrong_root() -> x509.Certificate:
    """A self-signed root unrelated to the fixture's chain, for a negative `certificateChain` test."""
    key = ed25519.Ed25519PrivateKey.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "conformance-test-wrong-root")])
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime(2020, 1, 1, tzinfo=dt.UTC))
        .not_valid_after(dt.datetime(2040, 1, 1, tzinfo=dt.UTC))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, None)
    )


def test_real_record_verifies_with_no_failed_check() -> None:
    """Every check the verifier performs on the real, unmodified record passes."""
    roots = TrustRoots.from_pem_file(_FIXTURE_DIR / "root.pem")
    report = AttributionVerifier(roots).verify(_record(), _image_bytes())
    assert not report.any_failed
    for name in _EXPECTED_PASSED:
        assert report.outcome(name) is CheckOutcome.PASSED, (name, report.outcome(name))
    assert report.outcome("manifestHash:xi-manifest") is CheckOutcome.NOT_RECOMPUTABLE


def test_lookup_record_no_manifests_collection_signature_not_performed() -> None:
    """A production record from a registration with no manifests (`fixtures/lookup/record.json`):
    `collectionSignature` is NOT_PERFORMED, not FAILED, since there is no collection to sign. This
    record chains to `CN=Institute of Provenance Root CA`, which is not carried in this repository,
    so it is verified here with the dev root instead and `certificateChain` fails for that reason
    alone.
    """
    record = json.loads((_LOOKUP_FIXTURE_DIR / "record.json").read_text(encoding="utf-8"))
    image = (_LOOKUP_FIXTURE_DIR / "image.png").read_bytes()
    roots = TrustRoots.from_pem_file(_FIXTURE_DIR / "root.pem")
    report = AttributionVerifier(roots).verify(record, image)

    for name in ("originalImageHash", "contentHash", "imageSignature", "leafKeyMatchesPublicKey"):
        assert report.outcome(name) is CheckOutcome.PASSED, (name, report.outcome(name))
    assert report.outcome("collectionSignature") is CheckOutcome.NOT_PERFORMED
    assert report.outcome("certificateChain") is CheckOutcome.FAILED
    assert [c.name for c in report.checks if c.outcome is CheckOutcome.FAILED] == ["certificateChain"]


def test_from_orbital_pinned_root_matches_root_pem_file() -> None:
    """`from_orbital`'s parsed root is the same certificate as `root.pem`, and it passes the chain check."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_orbital_info_bytes(), headers={"content-type": "application/json"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        orbital_roots = TrustRoots.from_orbital("https://orbital.example", client=client)

    file_roots = TrustRoots.from_pem_file(_FIXTURE_DIR / "root.pem")
    assert len(orbital_roots.certificates) == 1
    assert len(file_roots.certificates) == 1
    der = serialization.Encoding.DER
    assert orbital_roots.certificates[0].public_bytes(der) == file_roots.certificates[0].public_bytes(der)

    report = AttributionVerifier(orbital_roots).verify(_record(), _image_bytes())
    assert report.outcome("certificateChain") is CheckOutcome.PASSED


def test_wrong_pinned_root_fails_certificate_chain() -> None:
    """A root unrelated to the fixture's chain fails `certificateChain` on the real record."""
    roots = TrustRoots.from_pem([_wrong_root().public_bytes(serialization.Encoding.PEM).decode("ascii")])
    report = AttributionVerifier(roots).verify(_record(), _image_bytes())
    assert report.outcome("certificateChain") is CheckOutcome.FAILED


def test_tampered_c2pa_payload_byte_fails_manifest_hash() -> None:
    """Flipping one byte of the stored c2pa payload fails `manifestHash:c2pa`."""
    record = _record()
    c2pa = next(m for m in record["manifests"] if m["type"] == "c2pa")
    stored = bytearray(base64.b64decode(c2pa["payload"], validate=True))
    stored[0] ^= 0x01
    c2pa["payload"] = base64.b64encode(bytes(stored)).decode("ascii")

    roots = TrustRoots.from_pem_file(_FIXTURE_DIR / "root.pem")
    report = AttributionVerifier(roots).verify(record, _image_bytes())
    assert report.outcome("manifestHash:c2pa") is CheckOutcome.FAILED


@pytest.mark.parametrize("fixture_name", ["root.pem", "orbital-info.json", "record.json", "image.png"])
def test_fixture_files_exist(fixture_name: str) -> None:
    """Guard: the fixture directory carries every file these tests read."""
    assert (_FIXTURE_DIR / fixture_name).is_file()


def _legacy_record() -> dict[str, Any]:
    return json.loads((_LEGACY_FIXTURE_DIR / "record.json").read_text(encoding="utf-8"))


def test_legacy_record_verifies_with_every_performed_check_passed() -> None:
    """A real production record registered through the older Forensics Lab path
    (`fixtures/record-legacy/record.json`): `canonicalVersion: 0`, `hashAlgorithm: "blake3-256"`
    (lower-case), `contentHash` in upper-case hex, a single `c2pa` manifest with `hash: null` and
    `signature: null`, and no `collectionSignature`. Captured 2026-09-23 from the production
    Forensics Lab records endpoint (`POST /api/attribution/records`).
    The chain ends at `CN=Institute of Provenance Root CA`, which `fixtures/record/orbital-info.json`'s
    dev root does not carry, so the roots here were fetched from production Orbital's own `/info`
    instead (`fixtures/record-legacy/orbital-info.json`).
    """
    roots = TrustRoots.from_pem_file(_LEGACY_FIXTURE_DIR / "root.pem")
    report = AttributionVerifier(roots).verify(_legacy_record(), None)

    assert not report.any_failed
    assert report.all_performed_passed
    for name in ("originalImageHash", "imageSignature", "leafKeyMatchesPublicKey", "certificateChain"):
        assert report.outcome(name) is CheckOutcome.PASSED, (name, report.outcome(name))
    assert report.outcome("contentHash") is CheckOutcome.NOT_PERFORMED
    assert report.outcome("manifestHash:c2pa") is CheckOutcome.NOT_RECOMPUTABLE
    assert report.outcome("manifestSignature:c2pa") is CheckOutcome.NOT_RECOMPUTABLE
    assert report.outcome("collectionSignature") is CheckOutcome.NOT_PERFORMED


def test_legacy_record_from_orbital_pinned_root_matches_root_pem_file() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(_LEGACY_FIXTURE_DIR / "orbital-info.json").read_bytes(),
            headers={"content-type": "application/json"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        orbital_roots = TrustRoots.from_orbital("https://orbital.example", client=client)

    file_roots = TrustRoots.from_pem_file(_LEGACY_FIXTURE_DIR / "root.pem")
    der = serialization.Encoding.DER
    assert orbital_roots.certificates[0].public_bytes(der) == file_roots.certificates[0].public_bytes(der)

    report = AttributionVerifier(orbital_roots).verify(_legacy_record(), None)
    assert report.outcome("certificateChain") is CheckOutcome.PASSED


def test_legacy_record_tampered_image_signature_fails() -> None:
    record = _legacy_record()
    signature = bytearray(base64.b64decode(record["verification"]["signature"], validate=True))
    signature[0] ^= 0x01
    record["verification"]["signature"] = base64.b64encode(bytes(signature)).decode("ascii")

    roots = TrustRoots.from_pem_file(_LEGACY_FIXTURE_DIR / "root.pem")
    report = AttributionVerifier(roots).verify(record, None)
    assert report.outcome("imageSignature") is CheckOutcome.FAILED


@pytest.mark.parametrize("fixture_name", ["root.pem", "orbital-info.json", "record.json"])
def test_legacy_fixture_files_exist(fixture_name: str) -> None:
    """Guard: the legacy fixture directory carries every file these tests read."""
    assert (_LEGACY_FIXTURE_DIR / fixture_name).is_file()
