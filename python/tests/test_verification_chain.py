"""Certificate-chain tests for the attribution verifier: leaf-key match and the walk to a pinned root.

The CA and record-building helpers these tests share with `test_verification.py` live in
`verification_support.py`.
"""

from __future__ import annotations

import base64
import copy
import datetime as dt

from cryptography.hazmat.primitives.asymmetric import ed25519
from xio_parallax_client.verification import AttributionVerifier, CheckOutcome, TrustRoots

from .verification_support import (
    ORIGINAL,
    SIGNED_AT,
    Fixture,
    _ca,
    _chain_record,
    _intermediate_ca,
    _leaf_for,
    _pem,
    _verify,
    fixture,
)

__all__ = ["fixture"]


def test_wrong_root_fails_certificate_chain(fixture: Fixture) -> None:
    other_root, _ = _ca("Some Other Root")
    report = AttributionVerifier(TrustRoots.from_pem([_pem(other_root)])).verify(fixture.record, ORIGINAL)
    assert report.outcome("certificateChain") is CheckOutcome.FAILED
    assert report.passed("imageSignature")


def test_chain_leaf_intermediate_root_passes_when_root_pinned() -> None:
    root, root_key = _ca("Chain Root")
    intermediate, intermediate_key = _intermediate_ca("Chain Intermediate", root, root_key)
    leaf, signer = _leaf_for(intermediate, intermediate_key)
    record = _chain_record(leaf, signer, [leaf, intermediate, root])
    report = AttributionVerifier(TrustRoots.from_pem([_pem(root)])).verify(record)
    assert report.passed("certificateChain")


def test_chain_of_intermediate_only_passes() -> None:
    root, root_key = _ca("Chain Root")
    intermediate, intermediate_key = _intermediate_ca("Chain Intermediate", root, root_key)
    leaf, signer = _leaf_for(intermediate, intermediate_key)
    record = _chain_record(leaf, signer, [intermediate])
    report = AttributionVerifier(TrustRoots.from_pem([_pem(root)])).verify(record)
    assert report.passed("certificateChain")


def test_chain_leaf_intermediate_without_root_passes() -> None:
    root, root_key = _ca("Chain Root")
    intermediate, intermediate_key = _intermediate_ca("Chain Intermediate", root, root_key)
    leaf, signer = _leaf_for(intermediate, intermediate_key)
    record = _chain_record(leaf, signer, [leaf, intermediate])
    report = AttributionVerifier(TrustRoots.from_pem([_pem(root)])).verify(record)
    assert report.passed("certificateChain")


def test_chain_leaf_intermediate_root_fails_when_a_different_root_is_pinned() -> None:
    root, root_key = _ca("Chain Root")
    intermediate, intermediate_key = _intermediate_ca("Chain Intermediate", root, root_key)
    leaf, signer = _leaf_for(intermediate, intermediate_key)
    record = _chain_record(leaf, signer, [leaf, intermediate, root])
    different_root, _ = _ca("Chain Different Root")
    report = AttributionVerifier(TrustRoots.from_pem([_pem(different_root)])).verify(record)
    assert report.outcome("certificateChain") is CheckOutcome.FAILED


def test_chain_self_signed_terminal_root_fails_when_not_pinned() -> None:
    other_root, other_root_key = _ca("Chain Untrusted Root")
    intermediate, intermediate_key = _intermediate_ca("Chain Untrusted Intermediate", other_root, other_root_key)
    leaf, signer = _leaf_for(intermediate, intermediate_key)
    record = _chain_record(leaf, signer, [leaf, intermediate, other_root])
    # A real, pinned root, unrelated to this chain: `other_root` is self-signed but must never be trusted
    # merely because it looks like a root; only a pinned root by exact DER bytes/key can terminate the chain.
    pinned_root, _ = _ca("Chain Root")
    report = AttributionVerifier(TrustRoots.from_pem([_pem(pinned_root)])).verify(record)
    assert report.outcome("certificateChain") is CheckOutcome.FAILED


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
