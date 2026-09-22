"""Tests for the attribution verifier: preimages, hashes, signatures and trust-root bootstrap.

Certificate-chain tests live in `test_verification_chain.py`; the CA and record-building helpers both
files share live in `verification_support.py`.
"""

from __future__ import annotations

import base64
import copy
import json
import struct
from typing import Any

import blake3
import httpx
import pytest
from xio_parallax_client.verification import (
    AttributionVerifier,
    CanonicalPreimage,
    CheckOutcome,
    TrustRoots,
    VerificationRefused,
)

from .verification_support import JUMBF_BYTES, ORIGINAL, Fixture, _ca, _chain_record, _leaf_for, _pem, _verify, fixture

__all__ = ["fixture"]


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


def test_without_original_bytes_only_content_hash_is_not_performed(fixture: Fixture) -> None:
    report = _verify(fixture, original=None)
    outcomes = {c.name: c.outcome for c in report.checks}
    assert outcomes["originalImageHash"] is CheckOutcome.PASSED
    assert outcomes["contentHash"] is CheckOutcome.NOT_PERFORMED
    assert report.all_performed_passed


def test_wrong_original_bytes_fail_content_hash_only(fixture: Fixture) -> None:
    report = _verify(fixture, original=ORIGINAL + b"x")
    assert report.passed("originalImageHash")
    assert not report.passed("contentHash")
    assert report.any_failed and not report.all_performed_passed


def test_original_image_hash_mismatch_fails_regardless_of_bytes(fixture: Fixture) -> None:
    record = copy.deepcopy(fixture.record)
    record["originalImageHash"] = "0" * 64
    with_bytes = _verify(fixture, record, original=ORIGINAL)
    without_bytes = _verify(fixture, record, original=None)
    assert with_bytes.outcome("originalImageHash") is CheckOutcome.FAILED
    assert without_bytes.outcome("originalImageHash") is CheckOutcome.FAILED
    # contentHash is unaffected: it recomputes over the original bytes, not the record's own key.
    assert with_bytes.passed("contentHash")


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


def test_collection_signature_removed_with_manifests_fails(fixture: Fixture) -> None:
    """Manifests exist but `collectionSignature` is stripped: a FAILED verdict, not NOT_PERFORMED."""
    record = copy.deepcopy(fixture.record)
    record["verification"]["collectionSignature"] = None
    report = _verify(fixture, record)
    assert report.outcome("collectionSignature") is CheckOutcome.FAILED


def test_no_manifests_no_collection_signature_not_performed() -> None:
    """Zero manifests and no `collectionSignature`: nothing was ever there to sign, so NOT_PERFORMED."""
    root, root_key = _ca("No Manifests Root")
    leaf, signer = _leaf_for(root, root_key)
    record = _chain_record(leaf, signer, [root])
    report = AttributionVerifier(TrustRoots.from_pem([_pem(root)])).verify(record)
    assert report.outcome("collectionSignature") is CheckOutcome.NOT_PERFORMED


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
