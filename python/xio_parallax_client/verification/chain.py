"""The certificate chain walk: leaf-key match and the walk from leaf to a pinned root."""

from __future__ import annotations

import datetime

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ._record import NormalizedVerification
from .report import CheckOutcome, VerificationCheck
from .trust_roots import TrustRoots

_MAX_CHAIN_DEPTH = 8

_PASSED = CheckOutcome.PASSED
_FAILED = CheckOutcome.FAILED


def _valid_at(cert: x509.Certificate, when: datetime.datetime) -> bool:
    return cert.not_valid_before_utc <= when <= cert.not_valid_after_utc


def _is_ca(cert: x509.Certificate) -> tuple[bool, int | None]:
    try:
        constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
    except x509.ExtensionNotFound:
        return False, None
    if not constraints.ca:
        return False, None
    try:
        usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        return True, constraints.path_length
    if not usage.key_cert_sign:
        return False, None
    return True, constraints.path_length


def _issued_by(child: x509.Certificate, issuer: x509.Certificate) -> bool:
    """True when `issuer`'s subject is `child`'s issuer and `issuer`'s key verifies `child`'s signature."""
    try:
        child.verify_directly_issued_by(issuer)
    except (ValueError, TypeError, InvalidSignature):
        return False
    return True


def chain_checks(roots: TrustRoots, v: NormalizedVerification, key_raw: bytes | None) -> list[VerificationCheck]:
    """Parse the leaf certificate, check its key against `key_raw`, and walk the chain to a pinned root."""
    try:
        leaf = x509.load_pem_x509_certificate(v.leaf_certificate.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        detail = f"leafCertificate is not a PEM certificate: {exc}"
        return [
            VerificationCheck("leafKeyMatchesPublicKey", _FAILED, detail),
            VerificationCheck("certificateChain", _FAILED, detail),
        ]
    return [_leaf_key_check(leaf, key_raw), _chain_check(roots, leaf, v)]


def _leaf_key_check(leaf: x509.Certificate, key_raw: bytes | None) -> VerificationCheck:
    name = "leafKeyMatchesPublicKey"
    if key_raw is None:
        return VerificationCheck(name, _FAILED, "publicKey is not a raw 32-byte Ed25519 key")
    leaf_key = leaf.public_key()
    if not isinstance(leaf_key, Ed25519PublicKey):
        return VerificationCheck(name, _FAILED, f"leaf key is {type(leaf_key).__name__}, not Ed25519")
    if leaf_key.public_bytes_raw() != key_raw:
        return VerificationCheck(name, _FAILED, "leaf certificate's key differs from publicKey")
    return VerificationCheck(name, _PASSED, "leaf certificate's key equals publicKey")


def _chain_check(roots: TrustRoots, leaf: x509.Certificate, v: NormalizedVerification) -> VerificationCheck:
    """Walk leaf to a pinned root: issuer/subject linkage, issuer signatures, CA flags, validity at signing."""
    name = "certificateChain"
    try:
        intermediates: list[x509.Certificate] = []
        for pem in v.certificate_chain:
            intermediates.extend(x509.load_pem_x509_certificates(pem.encode("ascii")))
    except (ValueError, UnicodeEncodeError) as exc:
        return VerificationCheck(name, _FAILED, f"certificateChain holds a non-PEM entry: {exc}")

    when = v.signed_at_utc
    if not _valid_at(leaf, when):
        return VerificationCheck(name, _FAILED, f"leaf certificate is not valid at {when.isoformat()}")
    pinned = roots.certificates
    path: list[x509.Certificate] = [leaf]
    current = leaf
    for _ in range(_MAX_CHAIN_DEPTH):
        root = next((r for r in pinned if _issued_by(current, r)), None)
        if root is not None:
            failure = _issuer_failure(root, when, len(path) - 1)
            subject = root.subject.rfc4514_string()
            if failure:
                return VerificationCheck(name, _FAILED, f"pinned root {subject}: {failure}")
            return VerificationCheck(name, _PASSED, f"chains in {len(path)} step(s) to pinned root {subject}")
        issuer = next((c for c in intermediates if c not in path and _issued_by(current, c)), None)
        if issuer is None:
            return VerificationCheck(
                name, _FAILED, f"no issuer for {current.subject.rfc4514_string()} among the chain or pinned roots"
            )
        failure = _issuer_failure(issuer, when, len(path) - 1)
        if failure:
            return VerificationCheck(name, _FAILED, f"{issuer.subject.rfc4514_string()}: {failure}")
        path.append(issuer)
        current = issuer
    return VerificationCheck(name, _FAILED, f"no pinned root within {_MAX_CHAIN_DEPTH} steps")


def _issuer_failure(issuer: x509.Certificate, when: datetime.datetime, below: int) -> str | None:
    """Return why `issuer` cannot issue at `when` over `below` intermediates, or None when it can."""
    if not _valid_at(issuer, when):
        return f"not valid at {when.isoformat()}"
    is_ca, path_length = _is_ca(issuer)
    if not is_ca:
        return "not a CA (basicConstraints / keyUsage)"
    if path_length is not None and below > path_length:
        return f"path length {path_length} exceeded"
    return None
