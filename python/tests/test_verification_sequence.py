"""PC-120: a published sequence record verified end to end - its sequence hash and its summary signature.

Mirrors the .NET client's PC-119 suite. The preimage is proven against xio_parallax_common's own vectors,
vendored unmodified under `vectors/px-frame` (VECTORS.md names the commit) and discovered by glob, never a
hand-kept list; a missing vectors directory is a failure, not a skip.
"""

from __future__ import annotations

import base64
import copy
import datetime as dt
import json
from pathlib import Path
from typing import Any

import blake3
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from xio_parallax_client.verification import (
    CheckOutcome,
    SequenceSummaryPreimage,
    SummaryFrame,
    VerificationRefused,
)
from xio_parallax_client.verification.sequence import sequence_checks

from .verification_support import SIGNED_AT, Fixture, _ca, _name, _pem, _verify

_VECTORS_DIR = Path(__file__).resolve().parent / "vectors" / "px-frame"
_FRAME_IDS = [96, 12, 40]  # walk order, deliberately not frame-id order


def _vectors(folder: str) -> list[Path]:
    directory = _VECTORS_DIR / folder
    assert directory.is_dir(), f"the vendored vectors directory {directory} is missing"
    return sorted(directory.glob("*.json"))


@pytest.mark.parametrize("path", _vectors("sequence-summary"), ids=lambda p: p.stem)
def test_every_summary_vector_lays_out_byte_for_byte(path: Path) -> None:
    vector = json.loads(path.read_text(encoding="utf-8"))
    verdict = vector["verdict"]
    frames = [
        SummaryFrame(int(f["frameId"]), bytes.fromhex(f["originalImageHash"]), bytes.fromhex(f["frameHash"]))
        for f in vector["frames"]
    ]

    preimage = SequenceSummaryPreimage.build(
        bytes.fromhex(vector["sequenceHash"]),
        vector["expectedSize"],
        vector["finalSize"],
        verdict["connected"],
        verdict["sealed"],
        int(verdict["reach"]),
        verdict["framesReceived"],
        frames,
    )

    assert SequenceSummaryPreimage.frames_digest(frames).hex() == vector["framesDigest"]
    assert preimage.hex() == vector["preimage"]


@pytest.mark.parametrize("path", _vectors("sequence-hash"), ids=lambda p: p.stem)
def test_every_sequence_hash_vector_recomputes_through_the_checks(path: Path) -> None:
    vector = json.loads(path.read_text(encoding="utf-8"))
    sequence = {
        "frames": [
            {"frameId": str(index), "originalImageHash": "00" * 32, "frameHash": h}
            for index, h in enumerate(vector["bodyFrameHashesInWalkOrder"], start=1)
        ]
    }

    checks = sequence_checks(sequence, bytes.fromhex(vector["sequenceHash"]), None)

    assert checks[0].name == "sequenceHash"
    assert checks[0].outcome is CheckOutcome.PASSED


def _sign(key: ed25519.Ed25519PrivateKey, message: bytes) -> str:
    return base64.b64encode(key.sign(message)).decode("ascii")


def _sequence_fixture(sign_summary: bool = True) -> Fixture:
    """A sequence record as harness 0.16.0 publishes one, signed by a leaf under a fresh test root."""
    root, root_key = _ca("Sequence Test Root")
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
    frames = [
        SummaryFrame(i, blake3.blake3(f"image-{i}".encode()).digest(), blake3.blake3(f"frame-{i}".encode()).digest())
        for i in _FRAME_IDS
    ]
    sequence_hash = blake3.blake3(b"".join(f.frame_hash for f in frames)).digest()
    summary = SequenceSummaryPreimage.build(sequence_hash, 1800, len(frames), True, True, 172_790, len(frames), frames)
    record: dict[str, Any] = {
        "originalImageHash": sequence_hash.hex(),
        "outcome": "published",
        "manifests": [],
        "verification": {
            "contentHash": sequence_hash.hex(),
            "hashAlgorithm": "blake3-256",
            "signedAtUtc": SIGNED_AT.isoformat().replace("+00:00", "Z"),
            "signature": _sign(signer, sequence_hash),
            "signatureAlgorithm": "ed25519",
            "publicKey": base64.urlsafe_b64encode(signer.public_key().public_bytes_raw()).decode("ascii").rstrip("="),
            "leafCertificate": _pem(leaf),
            "certificateChain": [_pem(root)],
            "leafCertificateThumbprint": leaf.fingerprint(hashes.SHA256()).hex(),
            "trustContext": "test",
            "trustVersion": 1,
            "canonicalVersion": 2,
            "collectionSignature": None,
        },
        "failureReason": None,
        "membership": None,
        "sequence": {
            "expectedSize": 1800,
            "finalSize": len(frames),
            "verdict": {"connected": True, "sealed": True, "reach": 172_790, "framesReceived": len(frames)},
            "frames": [
                {
                    "frameId": f.frame_id,
                    "originalImageHash": f.original_image_hash.hex(),
                    "frameHash": f.frame_hash.hex(),
                }
                for f in frames
            ],
            "summaryPreimageVersion": 1 if sign_summary else None,
            "summarySignature": _sign(signer, summary) if sign_summary else None,
        },
    }
    return Fixture(record=record, root=root, signer=signer)


@pytest.fixture(scope="module")
def sequence_fixture() -> Fixture:
    return _sequence_fixture()


def test_a_faithful_sequence_record_passes_its_sequence_hash_and_summary_signature(sequence_fixture: Fixture) -> None:
    report = _verify(sequence_fixture, original=None)

    assert report.outcome("sequenceHash") is CheckOutcome.PASSED
    assert report.outcome("summarySignature") is CheckOutcome.PASSED
    assert report.outcome("imageSignature") is CheckOutcome.PASSED
    assert [c.name for c in report.checks[-2:]] == ["sequenceHash", "summarySignature"]
    assert not report.any_failed


@pytest.mark.parametrize("altered", ["image", "frameId", "reach", "expectedSize"])
def test_a_summary_altered_beside_its_frame_hashes_fails_the_signature_alone(
    sequence_fixture: Fixture, altered: str
) -> None:
    record = copy.deepcopy(sequence_fixture.record)
    sequence = record["sequence"]
    if altered == "image":
        sequence["frames"][0]["originalImageHash"] = blake3.blake3(b"another image").hexdigest()
    elif altered == "frameId":
        sequence["frames"][0]["frameId"] = 97
    elif altered == "reach":
        sequence["verdict"]["reach"] = 172_791
    else:
        sequence["expectedSize"] = None

    report = _verify(sequence_fixture, record, original=None)

    assert report.outcome("sequenceHash") is CheckOutcome.PASSED
    assert report.outcome("summarySignature") is CheckOutcome.FAILED


def test_a_frame_hash_out_of_place_fails_the_sequence_hash(sequence_fixture: Fixture) -> None:
    record = copy.deepcopy(sequence_fixture.record)
    frames = record["sequence"]["frames"]
    frames[0], frames[1] = frames[1], frames[0]

    report = _verify(sequence_fixture, record, original=None)

    assert report.outcome("sequenceHash") is CheckOutcome.FAILED
    assert report.outcome("summarySignature") is CheckOutcome.FAILED


def test_a_sequence_committed_before_summary_signing_reports_positions_as_not_proven_never_failed() -> None:
    fixture = _sequence_fixture(sign_summary=False)

    report = _verify(fixture, original=None)

    assert report.outcome("sequenceHash") is CheckOutcome.PASSED
    assert report.outcome("summarySignature") is CheckOutcome.NOT_PERFORMED
    assert "reported, not proven" in next(c.detail for c in report.checks if c.name == "summarySignature")
    assert not report.any_failed


def test_a_signature_without_its_preimage_version_fails(sequence_fixture: Fixture) -> None:
    record = copy.deepcopy(sequence_fixture.record)
    record["sequence"]["summaryPreimageVersion"] = None

    assert _verify(sequence_fixture, record, original=None).outcome("summarySignature") is CheckOutcome.FAILED


def test_a_preimage_version_this_verifier_does_not_lay_out_is_refused_by_name(sequence_fixture: Fixture) -> None:
    record = copy.deepcopy(sequence_fixture.record)
    record["sequence"]["summaryPreimageVersion"] = 2

    with pytest.raises(VerificationRefused, match="summaryPreimageVersion 2"):
        _verify(sequence_fixture, record, original=None)


def test_a_listed_frame_without_a_32_byte_hash_fails_both_checks_naming_it(sequence_fixture: Fixture) -> None:
    record = copy.deepcopy(sequence_fixture.record)
    record["sequence"]["frames"][2]["frameHash"] = "abcd"

    report = _verify(sequence_fixture, record, original=None)

    assert report.outcome("sequenceHash") is CheckOutcome.FAILED
    assert "listed frame 2" in next(c.detail for c in report.checks if c.name == "summarySignature")


def test_an_image_record_carries_no_sequence_checks(sequence_fixture: Fixture) -> None:
    record = copy.deepcopy(sequence_fixture.record)
    record["sequence"] = None

    report = _verify(sequence_fixture, record, original=None)

    assert "sequenceHash" not in [c.name for c in report.checks]
    assert "summarySignature" not in [c.name for c in report.checks]
