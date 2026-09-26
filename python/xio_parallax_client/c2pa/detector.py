"""Detection of embedded JUMBF manifest stores: identify the carrier, extract each store, walk and classify it.

REST never inspects a file's content; the client does. Each well-formed store is classified `c2pa` (its
description carries the C2PA manifest-store UUID and label) or `jumbf` (any other). What is found is
shown, and including it in a registration is the caller's explicit choice, through `as_manifest_part`
or a `ManifestSelection`.
"""

from __future__ import annotations

import struct
from collections import Counter
from collections.abc import Callable

from ..multipart import ManifestForm, ManifestPart
from .carriers import PNG_SIGNATURE, CarrierError, extract_jpeg, extract_png, extract_tiff, extract_webp
from .jumbf import C2PA_KIND, JUMBF_KIND, JumbfError, classify_store, read_store
from .models import C2paCarrier, EmbeddedC2paOutcome, EmbeddedC2paResult, EmbeddedC2paStore

__all__ = ["C2PA_KIND", "JUMBF_KIND", "as_manifest_part", "detect_embedded_c2pa", "jumbf_part"]

_Extractor = Callable[[bytes], list[bytes]]


def _identify(data: bytes) -> tuple[C2paCarrier, _Extractor | None, str]:
    """Match the file signature to a carrier; anything unrecognised is UNSUPPORTED, never 'no store'."""
    if data.startswith(b"\xff\xd8\xff"):
        return C2paCarrier.JPEG, extract_jpeg, ""
    if data.startswith(PNG_SIGNATURE):
        return C2paCarrier.PNG, extract_png, ""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return C2paCarrier.WEBP, extract_webp, ""
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return C2paCarrier.TIFF, extract_tiff, ""
    if data[:4] in (b"II+\x00", b"MM\x00+"):
        return C2paCarrier.UNSUPPORTED, None, "BigTIFF is not a supported carrier; nothing was looked for"
    return C2paCarrier.UNSUPPORTED, None, "unrecognised file signature; whether it carries a store is not known"


def _malformed(carrier: C2paCarrier, reason: str) -> EmbeddedC2paResult:
    """A MALFORMED result whose detail starts `malformed <CARRIER>:` and names what is wrong."""
    return EmbeddedC2paResult(carrier, EmbeddedC2paOutcome.MALFORMED, [], f"malformed {carrier.name}: {reason}")


def detect_embedded_c2pa(data: bytes) -> EmbeddedC2paResult:
    """Detect the JUMBF manifest stores embedded in `data` (JPEG APP11, PNG caBX, WebP C2PA, TIFF tag 0xCD41).

    Each store is walked and classified `c2pa` or `jumbf`; the outcome is FOUND with every store in
    document order. A store the walk refuses, or two stores of one kind, is MALFORMED (there is no
    pass-through of malformed bytes and nothing picks between two); a supported carrier with no store
    is ABSENT; an unrecognised format is UNSUPPORTED, never 'no store'.
    """
    carrier, extractor, refusal = _identify(data)
    if extractor is None:
        return EmbeddedC2paResult(carrier, EmbeddedC2paOutcome.UNSUPPORTED, [], refusal)
    try:
        raws = extractor(data)
    except (CarrierError, IndexError, struct.error) as exc:
        return _malformed(carrier, str(exc) if isinstance(exc, CarrierError) else "the file is truncated")
    if not raws:
        detail = f"{carrier.name} carries no embedded JUMBF manifest store"
        return EmbeddedC2paResult(carrier, EmbeddedC2paOutcome.ABSENT, [], detail)
    stores: list[EmbeddedC2paStore] = []
    for index, raw in enumerate(raws, start=1):
        try:
            boxes = read_store(raw)
            stores.append(EmbeddedC2paStore(data=raw, kind=classify_store(raw), boxes=boxes))
        except JumbfError as exc:
            return _malformed(carrier, f"embedded store {index} of {len(raws)}: {exc}")
    for kind, count in Counter(store.kind for store in stores).items():
        if count > 1:
            reason = f"{count} embedded manifest stores classify as kind {kind!r}; one kind carries one manifest"
            return _malformed(carrier, reason)
    detail = "; ".join(
        f"{store.kind} manifest store of {len(store.data)} bytes in {len(store.boxes)} JUMBF boxes" for store in stores
    )
    return EmbeddedC2paResult(carrier, EmbeddedC2paOutcome.FOUND, stores, detail)


def jumbf_part(kind: str, data: bytes) -> ManifestPart:
    """A classified JUMBF store as a `manifest[<kind>]` part: form C2PA for kind `c2pa`, else form JUMBF."""
    return ManifestPart(kind, ManifestForm.C2PA if kind == C2PA_KIND else ManifestForm.JUMBF, data)


def as_manifest_part(store: EmbeddedC2paStore) -> ManifestPart:
    """Wrap a detected store as a `manifest[<kind>]` part; the caller includes it explicitly, nothing else does."""
    return jumbf_part(store.kind, store.data)
