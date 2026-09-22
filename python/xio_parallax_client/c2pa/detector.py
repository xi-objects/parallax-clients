"""Detection of an embedded C2PA manifest store: identify the carrier, extract the store, show its boxes.

REST never inspects a file's content; the client does. What is found is shown, and attaching it to a
registration is the caller's explicit choice through `as_manifest_part`.
"""

from __future__ import annotations

import struct
from collections.abc import Callable

from ..multipart import ManifestForm, ManifestPart
from .carriers import PNG_SIGNATURE, CarrierError, extract_jpeg, extract_png, extract_tiff, extract_webp
from .jumbf import JumbfError, read_c2pa_store
from .models import C2paCarrier, EmbeddedC2paResult, EmbeddedC2paStore

#: The manifest kind an embedded C2PA store is attached under.
C2PA_MANIFEST_KIND = "c2pa"

_Extractor = Callable[[bytes], bytes | None]


def _identify(data: bytes) -> tuple[C2paCarrier, _Extractor | None, str]:
    """Match the file signature to a carrier; anything unrecognised is UNSUPPORTED, never 'no C2PA'."""
    if data.startswith(b"\xff\xd8\xff"):
        return C2paCarrier.JPEG, extract_jpeg, ""
    if data.startswith(PNG_SIGNATURE):
        return C2paCarrier.PNG, extract_png, ""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return C2paCarrier.WEBP, extract_webp, ""
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return C2paCarrier.TIFF, extract_tiff, ""
    if data[:4] in (b"II+\x00", b"MM\x00+"):
        return C2paCarrier.UNSUPPORTED, None, "BigTIFF is not a supported C2PA carrier; nothing was looked for"
    return C2paCarrier.UNSUPPORTED, None, "unrecognised file signature; whether it carries C2PA is not known"


def detect_embedded_c2pa(data: bytes) -> EmbeddedC2paResult:
    """Detect a C2PA manifest store embedded in `data` (JPEG APP11, PNG caBX, WebP C2PA, TIFF tag 0xCD41).

    `store` is None when the carrier is supported and holds no store, or when what the carrier holds
    is not a single well-formed `jumb` box described by the C2PA manifest-store UUID (the `detail`
    then starts `malformed <CARRIER>:` and names what is wrong; there is no pass-through of malformed
    bytes). An unrecognised format is `C2paCarrier.UNSUPPORTED`, never 'no C2PA'.
    """
    carrier, extractor, refusal = _identify(data)
    if extractor is None:
        return EmbeddedC2paResult(carrier=carrier, store=None, detail=refusal)
    try:
        raw = extractor(data)
    except (CarrierError, IndexError, struct.error) as exc:
        reason = str(exc) if isinstance(exc, CarrierError) else "the file is truncated"
        return EmbeddedC2paResult(carrier=carrier, store=None, detail=f"malformed {carrier.name}: {reason}")
    if raw is None:
        return EmbeddedC2paResult(carrier=carrier, store=None, detail=f"{carrier.name} carries no C2PA manifest store")
    try:
        boxes = read_c2pa_store(raw)
    except JumbfError as exc:
        return EmbeddedC2paResult(carrier=carrier, store=None, detail=f"malformed {carrier.name}: {exc}")
    detail = f"C2PA manifest store of {len(raw)} bytes in {len(boxes)} JUMBF boxes"
    return EmbeddedC2paResult(carrier=carrier, store=EmbeddedC2paStore(data=raw, boxes=boxes), detail=detail)


def as_manifest_part(store: EmbeddedC2paStore) -> ManifestPart:
    """Wrap a detected store as a `manifest[c2pa]` part; the caller attaches it explicitly, nothing does it for them."""
    return ManifestPart(C2PA_MANIFEST_KIND, ManifestForm.C2PA, store.data)
