"""Shared certificate and record-building helpers for the attribution-verifier tests."""

from __future__ import annotations

import base64
import datetime as dt
from dataclasses import dataclass
from typing import Any

import blake3
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.x509.oid import NameOID
from xio_parallax_client.generated.models import PublishedRecordResponse
from xio_parallax_client.verification import AttributionVerifier, CanonicalPreimage, TrustRoots, VerificationReport

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


def _intermediate_ca(
    cn: str, issuer_cert: x509.Certificate, issuer_key: ed25519.Ed25519PrivateKey, path_length: int | None = 0
) -> tuple[x509.Certificate, ed25519.Ed25519PrivateKey]:
    """A CA certificate signed by another CA, for certificate-chain shape tests."""
    key = ed25519.Ed25519PrivateKey.generate()
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name(cn))
        .issuer_name(issuer_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(SIGNED_AT - dt.timedelta(days=365))
        .not_valid_after(SIGNED_AT + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=path_length), critical=True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
        .sign(issuer_key, None)
    )
    return cert, key


def _leaf_for(
    issuer_cert: x509.Certificate, issuer_key: ed25519.Ed25519PrivateKey
) -> tuple[x509.Certificate, ed25519.Ed25519PrivateKey]:
    """A non-CA leaf certificate issued by the given CA, for certificate-chain shape tests."""
    signer = ed25519.Ed25519PrivateKey.generate()
    leaf = (
        x509.CertificateBuilder()
        .subject_name(_name("parallax signing service"))
        .issuer_name(issuer_cert.subject)
        .public_key(signer.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(SIGNED_AT - dt.timedelta(days=30))
        .not_valid_after(SIGNED_AT + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(issuer_key, None)
    )
    return leaf, signer


def _chain_record(
    leaf: x509.Certificate, signer: ed25519.Ed25519PrivateKey, chain: list[x509.Certificate]
) -> dict[str, Any]:
    """A minimal record carrying just what the `certificateChain` check needs."""
    content_hash = blake3.blake3(ORIGINAL).digest()
    public_raw = signer.public_key().public_bytes_raw()
    return {
        "originalImageHash": content_hash.hex(),
        "manifests": [],
        "verification": {
            "contentHash": content_hash.hex(),
            "hashAlgorithm": "blake3-256",
            "signedAtUtc": SIGNED_AT.isoformat().replace("+00:00", "Z"),
            "signature": _sign(signer, content_hash),
            "signatureAlgorithm": "ed25519",
            "publicKey": base64.urlsafe_b64encode(public_raw).decode("ascii").rstrip("="),
            "leafCertificate": _pem(leaf),
            "certificateChain": [_pem(c) for c in chain],
            "canonicalVersion": 2,
        },
    }


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
        "originalImageHash": content_hash.hex(),
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
            "hashAlgorithm": "blake3-256",  # the harness emits lower-case
            "signedAtUtc": SIGNED_AT.isoformat().replace("+00:00", "Z"),
            "signature": _sign(signer, content_hash),
            "signatureAlgorithm": "ed25519",
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
