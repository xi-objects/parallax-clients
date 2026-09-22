"""The attribution verifier: hashes, Ed25519 signatures over canonical v2 preimages, and the certificate chain."""

from __future__ import annotations

import base64
import binascii
import datetime
import hashlib
from typing import Any

import blake3
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ._record import NormalizedManifest, NormalizedRecord, NormalizedVerification, normalize_record
from .errors import VerificationRefused
from .preimage import CANONICAL_VERSION, CanonicalPreimage
from .report import CheckOutcome, VerificationCheck, VerificationReport
from .trust_roots import TrustRoots

_HASH_ALGORITHM = "BLAKE3-256"
_HASH_LENGTH = 32
_RECOMPUTABLE_FORMS = frozenset({"jumbf", "c2pa"})
_MAX_CHAIN_DEPTH = 8

_PASSED = CheckOutcome.PASSED
_FAILED = CheckOutcome.FAILED


def _b64_standard(text: str) -> bytes:
    return base64.b64decode(text, validate=True)


def _b64_either(text: str) -> bytes:
    """Decode base64url or standard base64, padding optional."""
    normalized = text.strip().replace("-", "+").replace("_", "/").rstrip("=")
    normalized += "=" * (-len(normalized) % 4)
    return base64.b64decode(normalized, validate=True)


def _ed25519_verify(key: Ed25519PublicKey | None, signature_b64: str | None, message: bytes) -> tuple[bool, str]:
    if key is None:
        return False, "publicKey is not a raw 32-byte Ed25519 key"
    if signature_b64 is None:
        return False, "record declares no signature"
    try:
        signature = _b64_standard(signature_b64)
    except (binascii.Error, ValueError):
        return False, "signature is not standard base64"
    try:
        key.verify(signature, message)
    except InvalidSignature:
        return False, "Ed25519 signature does not verify over the canonical preimage"
    return True, "Ed25519 signature verifies"


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


class AttributionVerifier:
    """Verifies a published attribution record against pinned trust roots, offline."""

    def __init__(self, roots: TrustRoots) -> None:
        """Bind the verifier to its pinned roots; no roots is a refusal."""
        if roots is None or not roots.certificates:
            raise VerificationRefused("Control not activated: no roots")
        self._roots = roots

    def verify(self, record: Any, original_image_bytes: bytes | None = None) -> VerificationReport:
        """Verify `record` (a `PublishedRecordResponse` or its JSON dict) and return a verdict per check.

        Raises `VerificationRefused` for a hash or signature algorithm other than BLAKE3-256 / Ed25519, a
        canonical version other than 2, a malformed content hash, a record without a verification block,
        or no trust roots.
        """
        if not self._roots.certificates:
            raise VerificationRefused("Control not activated: no roots")
        normalized = normalize_record(record)
        v = normalized.verification
        content_hash = self._preflight(v)

        report = VerificationReport()
        checks = report.checks
        checks.extend(self._original_hashes(normalized, content_hash, original_image_bytes))

        key, key_raw = self._public_key(v.public_key)
        entries: list[tuple[str, bytes] | None] = []
        for manifest in normalized.manifests:
            manifest_hash = self._manifest_hash_bytes(manifest)
            checks.append(self._manifest_hash_check(manifest, manifest_hash))
            checks.append(self._manifest_signature_check(manifest, manifest_hash, content_hash, key))
            entries.append(None if manifest_hash is None else (manifest.kind, manifest_hash))

        checks.append(self._collection_check(v, content_hash, entries, key))
        ok, detail = _ed25519_verify(key, v.signature, content_hash)
        checks.append(VerificationCheck("imageSignature", _PASSED if ok else _FAILED, detail))
        checks.extend(self._chain_checks(v, key_raw))
        return report

    @staticmethod
    def _preflight(v: NormalizedVerification) -> bytes:
        if v.canonical_version != CANONICAL_VERSION:
            raise VerificationRefused(f"canonicalVersion {v.canonical_version} is not implemented (only 2)")
        if v.hash_algorithm.upper() != _HASH_ALGORITHM:
            raise VerificationRefused(f"hashAlgorithm {v.hash_algorithm!r} is not implemented (only BLAKE3-256)")
        if v.signature_algorithm.lower() != "ed25519":
            raise VerificationRefused(f"signatureAlgorithm {v.signature_algorithm!r} is not implemented (only Ed25519)")
        try:
            content_hash = bytes.fromhex(v.content_hash)
        except ValueError as exc:
            raise VerificationRefused(f"contentHash is not hex: {v.content_hash!r}") from exc
        if len(content_hash) != _HASH_LENGTH:
            raise VerificationRefused(f"contentHash is {len(content_hash)} bytes; BLAKE3-256 is {_HASH_LENGTH}")
        return content_hash

    @staticmethod
    def _original_hashes(
        record: NormalizedRecord, content_hash: bytes, original: bytes | None
    ) -> list[VerificationCheck]:
        if original is None:
            detail = "original image bytes not supplied"
            return [
                VerificationCheck("originalImageHash", CheckOutcome.NOT_PERFORMED, detail),
                VerificationCheck("contentHash", CheckOutcome.NOT_PERFORMED, detail),
            ]
        sha = hashlib.sha256(original).hexdigest()
        sha_ok = sha == record.original_image_hash.lower()
        b3 = blake3.blake3(original).digest()
        b3_ok = b3 == content_hash
        return [
            VerificationCheck(
                "originalImageHash",
                _PASSED if sha_ok else _FAILED,
                "SHA-256 of the original matches" if sha_ok else f"SHA-256 of the original is {sha}",
            ),
            VerificationCheck(
                "contentHash",
                _PASSED if b3_ok else _FAILED,
                "BLAKE3-256 of the original matches" if b3_ok else f"BLAKE3-256 of the original is {b3.hex()}",
            ),
        ]

    @staticmethod
    def _public_key(text: str) -> tuple[Ed25519PublicKey | None, bytes | None]:
        try:
            raw = _b64_either(text)
            return Ed25519PublicKey.from_public_bytes(raw), raw
        except (binascii.Error, ValueError):
            return None, None

    @staticmethod
    def _manifest_hash_bytes(manifest: NormalizedManifest) -> bytes | None:
        if manifest.hash_hex is None:
            return None
        try:
            return bytes.fromhex(manifest.hash_hex)
        except ValueError:
            return None

    @staticmethod
    def _stored_bytes(manifest: NormalizedManifest) -> bytes | None:
        payload = manifest.payload
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
        if isinstance(payload, str):
            try:
                return _b64_standard(payload)
            except (binascii.Error, ValueError):
                return None
        return None

    def _manifest_hash_check(self, manifest: NormalizedManifest, declared: bytes | None) -> VerificationCheck:
        name = f"manifestHash:{manifest.kind}"
        if manifest.form not in _RECOMPUTABLE_FORMS:
            return VerificationCheck(
                name,
                CheckOutcome.NOT_RECOMPUTABLE,
                f"form {manifest.form!r}: the stored bytes are the carrier's own JUMBF and are not returned",
            )
        if declared is None:
            return VerificationCheck(name, _FAILED, "record declares no hex manifest hash")
        stored = self._stored_bytes(manifest)
        if stored is None:
            return VerificationCheck(name, _FAILED, f"form {manifest.form!r} payload is not bytes or base64 text")
        recomputed = blake3.blake3(stored).digest()
        if recomputed == declared:
            return VerificationCheck(name, _PASSED, "BLAKE3-256 of the payload matches the declared hash")
        return VerificationCheck(name, _FAILED, f"BLAKE3-256 of the payload is {recomputed.hex()}")

    @staticmethod
    def _manifest_signature_check(
        manifest: NormalizedManifest,
        manifest_hash: bytes | None,
        content_hash: bytes,
        key: Ed25519PublicKey | None,
    ) -> VerificationCheck:
        name = f"manifestSignature:{manifest.kind}"
        if manifest_hash is None:
            return VerificationCheck(name, _FAILED, "record declares no hex manifest hash to sign over")
        preimage = CanonicalPreimage.manifest(content_hash, manifest.kind, manifest_hash)
        ok, detail = _ed25519_verify(key, manifest.signature_b64, preimage)
        return VerificationCheck(name, _PASSED if ok else _FAILED, detail)

    @staticmethod
    def _collection_check(
        v: NormalizedVerification,
        content_hash: bytes,
        entries: list[tuple[str, bytes] | None],
        key: Ed25519PublicKey | None,
    ) -> VerificationCheck:
        name = "collectionSignature"
        if v.collection_signature is None:
            return VerificationCheck(name, _FAILED, "record declares no collection signature")
        complete = [e for e in entries if e is not None]
        if len(complete) != len(entries):
            return VerificationCheck(name, _FAILED, "a manifest declares no hex hash; the collection cannot be built")
        preimage = CanonicalPreimage.collection(content_hash, complete)
        ok, detail = _ed25519_verify(key, v.collection_signature, preimage)
        return VerificationCheck(name, _PASSED if ok else _FAILED, detail)

    def _chain_checks(self, v: NormalizedVerification, key_raw: bytes | None) -> list[VerificationCheck]:
        try:
            leaf = x509.load_pem_x509_certificate(v.leaf_certificate.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            detail = f"leafCertificate is not a PEM certificate: {exc}"
            return [
                VerificationCheck("leafKeyMatchesPublicKey", _FAILED, detail),
                VerificationCheck("certificateChain", _FAILED, detail),
            ]
        return [self._leaf_key_check(leaf, key_raw), self._chain_check(leaf, v)]

    @staticmethod
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

    def _chain_check(self, leaf: x509.Certificate, v: NormalizedVerification) -> VerificationCheck:
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
        roots = self._roots.certificates
        path: list[x509.Certificate] = [leaf]
        current = leaf
        for _ in range(_MAX_CHAIN_DEPTH):
            root = next((r for r in roots if _issued_by(current, r)), None)
            if root is not None:
                failure = self._issuer_failure(root, when, len(path) - 1)
                subject = root.subject.rfc4514_string()
                if failure:
                    return VerificationCheck(name, _FAILED, f"pinned root {subject}: {failure}")
                return VerificationCheck(name, _PASSED, f"chains in {len(path)} step(s) to pinned root {subject}")
            issuer = next((c for c in intermediates if c not in path and _issued_by(current, c)), None)
            if issuer is None:
                return VerificationCheck(
                    name, _FAILED, f"no issuer for {current.subject.rfc4514_string()} among the chain or pinned roots"
                )
            failure = self._issuer_failure(issuer, when, len(path) - 1)
            if failure:
                return VerificationCheck(name, _FAILED, f"{issuer.subject.rfc4514_string()}: {failure}")
            path.append(issuer)
            current = issuer
        return VerificationCheck(name, _FAILED, f"no pinned root within {_MAX_CHAIN_DEPTH} steps")

    @staticmethod
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
