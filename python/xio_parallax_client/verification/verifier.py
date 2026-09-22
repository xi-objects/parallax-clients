"""The attribution verifier: hashes, Ed25519 signatures over canonical v2 preimages, and the certificate chain."""

from __future__ import annotations

import base64
import binascii
from typing import Any

import blake3
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ._record import NormalizedManifest, NormalizedRecord, NormalizedVerification, normalize_record
from .chain import chain_checks
from .errors import VerificationRefused
from .preimage import CANONICAL_VERSION, CanonicalPreimage
from .report import CheckOutcome, VerificationCheck, VerificationReport
from .trust_roots import TrustRoots

_HASH_ALGORITHM = "BLAKE3-256"
_HASH_LENGTH = 32
_RECOMPUTABLE_FORMS = frozenset({"jumbf", "c2pa"})

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
        checks.extend(chain_checks(self._roots, v, key_raw))
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
        """`originalImageHash` is the record's own key (`= verification.contentHash`, checked either way);
        `contentHash` recomputes BLAKE3-256 over the supplied original and is NOT_PERFORMED without it."""
        content_hash_hex = content_hash.hex()
        keyed_ok = record.original_image_hash.lower() == content_hash_hex
        detail = (
            "originalImageHash equals verification.contentHash"
            if keyed_ok
            else f"originalImageHash is {record.original_image_hash!r}, contentHash is {content_hash_hex!r}"
        )
        original_check = VerificationCheck("originalImageHash", _PASSED if keyed_ok else _FAILED, detail)
        if original is None:
            not_performed = VerificationCheck("contentHash", CheckOutcome.NOT_PERFORMED, "original image bytes not supplied")
            return [original_check, not_performed]
        b3_ok = blake3.blake3(original).digest() == content_hash
        b3_detail = "BLAKE3-256 of the original matches" if b3_ok else "BLAKE3-256 of the original differs"
        return [original_check, VerificationCheck("contentHash", _PASSED if b3_ok else _FAILED, b3_detail)]

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

