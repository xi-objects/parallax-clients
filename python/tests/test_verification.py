"""Tests for the attribution verifier: preimages, hashes, signatures, chain and trust-root bootstrap."""

from __future__ import annotations

import base64
import copy
import datetime as dt
import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Any

import blake3
import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.x509.oid import NameOID
from xio_parallax_client.generated.models import PublishedRecordResponse
from xio_parallax_client.verification import (
    AttributionVerifier,
    CanonicalPreimage,
    CheckOutcome,
    TrustRoots,
    VerificationRefused,
    VerificationReport,
)

SIGNED_AT = dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC)
ORIGINAL = b"\x89PNG\r\n\x1a\n pretend image bytes"
JUMBF_BYTES = b"\x00\x00\x00\x20jumb\x00\x00\x00\x18jumdc2pa pretend claim bytes"
XI_MANIFEST = {"creator": "someone", "tool": "tests"}
XI_STORED = b"carrier jumbf bytes that the record never returns"


def _pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


def _name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _ca(cn: str) -> tuple[x509.Certificate, ed25519.Ed25519PrivateKey]:
    key = ed25519.Ed25519PrivateKey.generate()
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name(cn))
        .issuer_name(_name(cn))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(SIGNED_AT - dt.timedelta(days=365))
        .not_valid_after(SIGNED_AT + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
        .sign(key, None)
    )
    return cert, key


@dataclass
class Fixture:
    """A signed record with the root that anchors it and the key that signed it."""

    record: dict[str, Any]
    root: x509.Certificate
    signer: ed25519.Ed25519PrivateKey


def _sign(key: ed25519.Ed25519PrivateKey, message: bytes) -> str:
    return base64.b64encode(key.sign(message)).decode("ascii")


def _build() -> Fixture:
    root, root_key = _ca("Test Root")
    signer = ed25519.Ed25519PrivateKey.generate()
    leaf = (
        x509.CertificateBuilder()
        .subject_name(_name("parallax signing service"))
        .issuer_name(root.subject)
        .public_key(signer.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(SIGNED_AT - dt.timedelta(days=30))
        .not_valid_after(SIGNED_AT + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(root_key, None)
    )
    content_hash = blake3.blake3(ORIGINAL).digest()
    c2pa_hash = blake3.blake3(JUMBF_BYTES).digest()
    xi_hash = blake3.blake3(XI_STORED).digest()
    entries = [("c2pa", c2pa_hash), ("xi-manifest", xi_hash)]
    public_raw = signer.public_key().public_bytes_raw()
    record = {
        "originalImageHash": hashlib.sha256(ORIGINAL).hexdigest(),
        "outcome": "published",
        "manifests": [
            {
                "type": kind,
                "form": form,
                "payload": payload,
                "hash": mhash.hex(),
                "signature": _sign(signer, CanonicalPreimage.manifest(content_hash, kind, mhash)),
            }
            for (kind, mhash), form, payload in zip(
                entries,
                ["jumbf", "json"],
                [base64.b64encode(JUMBF_BYTES).decode("ascii"), XI_MANIFEST],
                strict=True,
            )
        ],
        "verification": {
            "contentHash": content_hash.hex(),
            "hashAlgorithm": "BLAKE3-256",
            "signedAtUtc": SIGNED_AT.isoformat().replace("+00:00", "Z"),
            "signature": _sign(signer, content_hash),
            "signatureAlgorithm": "Ed25519",
            "publicKey": base64.urlsafe_b64encode(public_raw).decode("ascii").rstrip("="),
            "leafCertificate": _pem(leaf),
            "certificateChain": [_pem(root)],
            "leafCertificateThumbprint": leaf.fingerprint(hashes.SHA256()).hex(),
            "trustContext": "test",
            "trustVersion": 1,
            "canonicalVersion": 2,
            "collectionSignature": _sign(signer, CanonicalPreimage.collection(content_hash, entries)),
        },
        "failureReason": None,
    }
    return Fixture(record=record, root=root, signer=signer)


@pytest.fixture(scope="module")
def fixture() -> Fixture:
    return _build()


def _verify(fx: Fixture, record: Any = None, original: bytes | None = ORIGINAL) -> VerificationReport:
    roots = TrustRoots.from_pem([_pem(fx.root)])
    target = PublishedRecordResponse.from_dict(fx.record if record is None else record)
    return AttributionVerifier(roots).verify(target, original)


def test_all_performed_checks_pass(fixture: Fixture) -> None:
    report = _verify(fixture)
    names = [c.name for c in report.checks]
    assert names == [
        "originalImageHash",
        "contentHash",
        "manifestHash:c2pa",
        "manifestSignature:c2pa",
        "manifestHash:xi-manifest",
        "manifestSignature:xi-manifest",
        "collectionSignature",
        "imageSignature",
        "leafKeyMatchesPublicKey",
        "certificateChain",
    ]
    assert report.all_performed_passed, [c for c in report.checks if c.outcome is not CheckOutcome.PASSED]
    assert not report.any_failed
    assert report.passed("certificateChain")
    assert report.passed("contentHash") and report.passed("originalImageHash")


def test_json_form_manifest_hash_is_not_recomputable(fixture: Fixture) -> None:
    report = _verify(fixture)
    check = next(c for c in report.checks if c.name == "manifestHash:xi-manifest")
    assert check.outcome is CheckOutcome.NOT_RECOMPUTABLE
    assert not report.passed("manifestHash:xi-manifest")


def test_without_original_bytes_hash_recomputes_are_not_performed(fixture: Fixture) -> None:
    report = _verify(fixture, original=None)
    outcomes = {c.name: c.outcome for c in report.checks}
    assert outcomes["originalImageHash"] is CheckOutcome.NOT_PERFORMED
    assert outcomes["contentHash"] is CheckOutcome.NOT_PERFORMED
    assert report.all_performed_passed


def test_wrong_original_bytes_fail_both_hashes(fixture: Fixture) -> None:
    report = _verify(fixture, original=ORIGINAL + b"x")
    assert not report.passed("originalImageHash") and not report.passed("contentHash")
    assert report.any_failed and not report.all_performed_passed


def _tampered_jumbf() -> bytes:
    tampered = bytearray(JUMBF_BYTES)
    tampered[10] ^= 0x01
    return bytes(tampered)


def test_tampered_manifest_hash_byte_fails_hash_and_signature(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    declared = bytearray.fromhex(record["manifests"][0]["hash"])
    declared[0] ^= 0x01
    record["manifests"][0]["hash"] = declared.hex()
    report = _verify(fixture, record)
    assert report.outcome("manifestHash:c2pa") is CheckOutcome.FAILED
    assert report.outcome("manifestSignature:c2pa") is CheckOutcome.FAILED
    assert report.outcome("collectionSignature") is CheckOutcome.FAILED
    assert report.passed("manifestSignature:xi-manifest")


def test_tampered_payload_byte_fails_manifest_hash(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    record["manifests"][0]["payload"] = base64.b64encode(_tampered_jumbf()).decode("ascii")
    report = _verify(fixture, record)
    assert report.outcome("manifestHash:c2pa") is CheckOutcome.FAILED


def test_tampered_payload_with_rehashed_declaration_fails_signature(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    record["manifests"][0]["payload"] = base64.b64encode(_tampered_jumbf()).decode("ascii")
    record["manifests"][0]["hash"] = blake3.blake3(_tampered_jumbf()).hexdigest()
    report = _verify(fixture, record)
    assert report.passed("manifestHash:c2pa")
    assert report.outcome("manifestSignature:c2pa") is CheckOutcome.FAILED
    assert report.outcome("collectionSignature") is CheckOutcome.FAILED


def test_stripped_manifest_fails_collection_signature(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    del record["manifests"][1]
    report = _verify(fixture, record)
    assert report.passed("manifestSignature:c2pa")
    assert report.outcome("collectionSignature") is CheckOutcome.FAILED


def test_wrong_root_fails_certificate_chain(fixture: Fixture) -> None:
    other_root, _ = _ca("Some Other Root")
    report = AttributionVerifier(TrustRoots.from_pem([_pem(other_root)])).verify(fixture.record, ORIGINAL)
    assert report.outcome("certificateChain") is CheckOutcome.FAILED
    assert report.passed("imageSignature")


def test_leaf_outside_validity_at_signing_fails_chain(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    record["verification"]["signedAtUtc"] = (SIGNED_AT + dt.timedelta(days=60)).isoformat()
    report = _verify(fixture, record)
    assert report.outcome("certificateChain") is CheckOutcome.FAILED


def test_wrong_public_key_fails_leaf_match(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    other = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    record["verification"]["publicKey"] = base64.b64encode(other).decode("ascii")
    report = _verify(fixture, record)
    assert report.outcome("leafKeyMatchesPublicKey") is CheckOutcome.FAILED
    assert report.outcome("imageSignature") is CheckOutcome.FAILED


@pytest.mark.parametrize(
    ("field", "value"),
    [("hashAlgorithm", "SHA-256"), ("canonicalVersion", 1), ("canonicalVersion", "1"), ("signatureAlgorithm", "RSA")],
)
def test_refusals(fixture: Fixture, field: str, value: Any) -> None:
    record = copy.deepcopy(fixture.record)
    record["verification"][field] = value
    with pytest.raises(VerificationRefused) as caught:
        _verify(fixture, record)
    assert str(value) in str(caught.value)


def test_empty_roots_refused() -> None:
    with pytest.raises(VerificationRefused, match="no roots"):
        TrustRoots.from_pem([])
    with pytest.raises(VerificationRefused, match="no roots"):
        TrustRoots([])


def test_verifies_from_plain_dict(fixture: Fixture) -> None:
    record = json.loads(json.dumps(fixture.record))
    record["verification"]["canonicalVersion"] = "2"
    report = AttributionVerifier(TrustRoots.from_pem([_pem(fixture.root)])).verify(record, ORIGINAL)
    assert report.all_performed_passed
    assert report.outcome("manifestHash:xi-manifest") is CheckOutcome.NOT_RECOMPUTABLE


def test_from_orbital_parses_pinned_roots(fixture: Fixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://orbital.example/info")
        return httpx.Response(200, json={"name": "orbital", "PinnedRoots": [_pem(fixture.root)]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        roots = TrustRoots.from_orbital("https://orbital.example/", client=client)
    assert roots.certificates == (fixture.root,)
    assert AttributionVerifier(roots).verify(fixture.record, ORIGINAL).all_performed_passed


def test_from_orbital_refuses_empty_roots() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"pinnedRoots": []}))
    with httpx.Client(transport=transport) as client, pytest.raises(VerificationRefused, match="no roots"):
        TrustRoots.from_orbital("https://orbital.example", client=client)


async def test_from_orbital_async_parses_pinned_roots(fixture: Fixture) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"pinnedRoots": [_pem(fixture.root)]}))
    async with httpx.AsyncClient(transport=transport) as client:
        roots = await TrustRoots.from_orbital_async("https://orbital.example", client=client)
    assert roots.certificates == (fixture.root,)


def test_manifest_preimage_bytes() -> None:
    content = bytes(range(32))
    mhash = bytes(range(100, 132))
    expected = b"\x02" + b"\x00\x20" + content + b"\x00\x04" + b"c2pa" + b"\x00\x20" + mhash
    assert CanonicalPreimage.manifest(content, "c2pa", mhash) == expected


def test_collection_preimage_bytes() -> None:
    content = b"\xaa" * 32
    h1, h2 = b"\x01" * 32, b"\x02" * 32
    expected = (
        b"\x02"
        + struct.pack(">H", 32)
        + content
        + b"\x00\x02"
        + b"\x00\x04c2pa"
        + b"\x00\x20"
        + h1
        + b"\x00\x0bxi-manifest"
        + b"\x00\x20"
        + h2
    )
    assert CanonicalPreimage.collection(content, [("c2pa", h1), ("xi-manifest", h2)]) == expected
    assert CanonicalPreimage.collection(content, []) == b"\x02\x00\x20" + content + b"\x00\x00"


def test_verifies_nested_manifest_dict_shape_with_c2pa_form(fixture: Fixture) -> None:
    record = json.loads(json.dumps(fixture.record))
    record["manifests"] = [
        {
            "manifest": {
                "type": m["type"],
                "form": "c2pa" if m["form"] == "jumbf" else m["form"],
                "payload": m["payload"],
            },
            "hash": m["hash"],
            "signature": m["signature"],
        }
        for m in record["manifests"]
    ]
    report = AttributionVerifier(TrustRoots.from_pem([_pem(fixture.root)])).verify(record)
    assert report.passed("manifestHash:c2pa")
    assert report.all_performed_passed
