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
