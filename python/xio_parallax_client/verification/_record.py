"""Normalization of a published record (generated model or plain JSON dict) into one internal shape."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .errors import VerificationRefused


@dataclass(frozen=True)
class NormalizedManifest:
    """One manifest off a record: kind, form, payload, declared hash (hex) and signature (base64)."""

    kind: str
    form: str
    payload: Any
    hash_hex: str | None
    signature_b64: str | None


@dataclass(frozen=True)
class NormalizedVerification:
    """The fields of a record's verification block that verification consumes."""

    content_hash: str
    hash_algorithm: str
    signed_at_utc: datetime.datetime
    signature: str
    signature_algorithm: str
    public_key: str
    leaf_certificate: str
    certificate_chain: list[str]
    canonical_version: int
    collection_signature: str | None


@dataclass(frozen=True)
class NormalizedRecord:
    """A published record in the one shape the verifier works on."""

    original_image_hash: str
    manifests: list[NormalizedManifest]
    verification: NormalizedVerification


def _optional_str(value: Any) -> str | None:
    """Map UNSET / None to None; keep strings; refuse anything else."""
    if value is None or type(value).__name__ == "Unset":
        return None
    if isinstance(value, str):
        return value
    raise VerificationRefused(f"expected a string, got {type(value).__name__}")


def _require(mapping: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise VerificationRefused(f"record is missing {where}{key}")
    return mapping[key]


def _as_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise VerificationRefused(f"{name} is not an integer: {value!r}") from exc


def _as_datetime(value: Any) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except ValueError as exc:
            raise VerificationRefused(f"signedAtUtc is not an ISO-8601 timestamp: {value!r}") from exc
    else:
        raise VerificationRefused(f"signedAtUtc is not a timestamp: {value!r}")
    if parsed.tzinfo is None:
        # The field is named and documented as UTC.
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed


def _manifest_from_mapping(item: Mapping[str, Any]) -> NormalizedManifest:
    return NormalizedManifest(
        kind=str(_require(item, "type", "manifest.")),
        form=str(_require(item, "form", "manifest.")).lower(),
        payload=_require(item, "payload", "manifest."),
        hash_hex=_optional_str(item.get("hash", item.get("hash_"))),
        signature_b64=_optional_str(item.get("signature")),
    )


def _manifest(item: Any) -> NormalizedManifest:
    if isinstance(item, Mapping):
        inner = item.get("manifest")
        if isinstance(inner, Mapping):
            merged = dict(inner)
            merged["hash"] = item.get("hash", item.get("hash_"))
            merged["signature"] = item.get("signature")
            return _manifest_from_mapping(merged)
        return _manifest_from_mapping(item)
    return NormalizedManifest(
        kind=str(item.type_),
        form=str(item.form).lower(),
        payload=item.payload,
        hash_hex=_optional_str(item.hash_),
        signature_b64=_optional_str(item.signature),
    )


def _verification_from_mapping(v: Mapping[str, Any]) -> NormalizedVerification:
    where = "verification."
    chain = _require(v, "certificateChain", where)
    if not isinstance(chain, list) or not all(isinstance(c, str) for c in chain):
        raise VerificationRefused("verification.certificateChain is not a list of PEM strings")
    return NormalizedVerification(
        content_hash=str(_require(v, "contentHash", where)),
        hash_algorithm=str(_require(v, "hashAlgorithm", where)),
        signed_at_utc=_as_datetime(_require(v, "signedAtUtc", where)),
        signature=str(_require(v, "signature", where)),
        signature_algorithm=str(_require(v, "signatureAlgorithm", where)),
        public_key=str(_require(v, "publicKey", where)),
        leaf_certificate=str(_require(v, "leafCertificate", where)),
        certificate_chain=list(chain),
        canonical_version=_as_int(_require(v, "canonicalVersion", where), "canonicalVersion"),
        collection_signature=_optional_str(v.get("collectionSignature")),
    )


def _verification(v: Any) -> NormalizedVerification:
    if v is None:
        raise VerificationRefused("record carries no verification block")
    if isinstance(v, Mapping):
        return _verification_from_mapping(v)
    return NormalizedVerification(
        content_hash=v.content_hash,
        hash_algorithm=v.hash_algorithm,
        signed_at_utc=_as_datetime(v.signed_at_utc),
        signature=v.signature,
        signature_algorithm=v.signature_algorithm,
        public_key=v.public_key,
        leaf_certificate=v.leaf_certificate,
        certificate_chain=list(v.certificate_chain),
        canonical_version=_as_int(v.canonical_version, "canonicalVersion"),
        collection_signature=_optional_str(v.collection_signature),
    )


def normalize_record(record: Any) -> NormalizedRecord:
    """Normalize a `PublishedRecordResponse` or its plain JSON dict into a `NormalizedRecord`."""
    if isinstance(record, Mapping):
        original = _require(record, "originalImageHash", "")
        manifests_raw = record.get("manifests")
        verification_raw = record.get("verification")
    else:
        original = record.original_image_hash
        manifests_raw = record.manifests
        verification_raw = record.verification
    if manifests_raw is not None and not isinstance(manifests_raw, list):
        raise VerificationRefused("record.manifests is not a list")
    return NormalizedRecord(
        original_image_hash=str(original),
        manifests=[_manifest(m) for m in (manifests_raw or [])],
        verification=_verification(verification_raw),
    )
