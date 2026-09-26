"""The manifest selection and the conflict rule, resolved over a whole collection before anything is sent.

Per image the caller's user chooses whether the embedded JUMBF manifest store(s) are included and which
sidecars go beside them: JSON (kind stated by the caller) or JUMBF (kind classified from its own bytes,
`c2pa` or `jumbf`). When the image holds embedded stores and JUMBF sidecars are given, the distinct
sidecar bytes and the distinct embedded bytes must be equal sets (a sidecar matching no store, or a store
matching no sidecar, refuses), and each distinct manifest is included once whatever `include_embedded`
says; with no embedded store the sidecars go in; with no JUMBF sidecar the stores go in only when
`include_embedded`. Two manifests of one kind refuse. Whenever the embedded
store matters (`include_embedded`, or any JUMBF sidecar) a malformed store or an unrecognised carrier
refuses, since the check is never skipped. Any refusal refuses the whole collection, every offending
image listed; the register calls themselves send exactly the manifests they are given.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .c2pa.detector import detect_embedded_c2pa, jumbf_part
from .c2pa.jumbf import JumbfError, classify_store, read_store
from .c2pa.models import EmbeddedC2paOutcome
from .multipart import ImageUpload, ManifestForm, ManifestPart, validate_manifest_kind
from .slots import RegistrationItem


@dataclass(frozen=True, slots=True)
class SidecarManifest:
    """One manifest supplied beside an image rather than embedded in it.

    `name` is what a refusal calls it (a file name). `form` is JSON, whose `kind` the caller states, or
    JUMBF, whose kind is classified from its own bytes and so must be None here. C2PA is a
    classification result, never an input form, and is refused.
    """

    name: str
    form: ManifestForm
    kind: str | None
    data: bytes

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a sidecar needs a name, the file name its refusals are reported under")
        if self.form is ManifestForm.C2PA:
            raise ValueError(
                f"sidecar {self.name!r}: form C2PA is a classification of JUMBF bytes, never an input; give it as JUMBF"
            )
        if self.form is ManifestForm.JSON:
            if self.kind is None:
                raise ValueError(f"JSON sidecar {self.name!r} needs the manifest kind it is sent under")
            validate_manifest_kind(self.kind)
        elif self.kind is not None:
            raise ValueError(f"JUMBF sidecar {self.name!r} takes no kind: its kind is classified from its own bytes")

    @classmethod
    def json(cls, name: str, kind: str, data: bytes) -> SidecarManifest:
        """A JSON sidecar sent as `manifest[<kind>]`."""
        return cls(name=name, form=ManifestForm.JSON, kind=kind, data=data)

    @classmethod
    def jumbf(cls, name: str, data: bytes) -> SidecarManifest:
        """A JUMBF sidecar whose kind is classified from its bytes at resolution."""
        return cls(name=name, form=ManifestForm.JUMBF, kind=None, data=data)

    @classmethod
    def json_file(cls, path: str | Path, kind: str) -> SidecarManifest:
        """Read a JSON sidecar off disk; its file name is its name."""
        file_path = Path(path)
        return cls.json(file_path.name, kind, file_path.read_bytes())

    @classmethod
    def jumbf_file(cls, path: str | Path) -> SidecarManifest:
        """Read a JUMBF sidecar off disk; its file name is its name."""
        file_path = Path(path)
        return cls.jumbf(file_path.name, file_path.read_bytes())


@dataclass(frozen=True, slots=True)
class ManifestSelection:
    """Which manifests one image carries: its embedded store(s) or not, and the sidecars, in wire order."""

    include_embedded: bool
    sidecars: Sequence[SidecarManifest] = ()


#: The selection that registers an image with no manifest at all.
NO_MANIFESTS = ManifestSelection(include_embedded=False)


@dataclass(frozen=True, slots=True)
class ManifestRequest:
    """One image and the manifest selection its user chose for it."""

    image: ImageUpload
    selection: ManifestSelection


@dataclass(frozen=True, slots=True)
class ManifestRefusal:
    """Why one image's manifests were refused: the image's file name and one reason."""

    file_name: str
    reason: str


class ManifestRefusalError(ValueError):
    """Manifest resolution refused; `refusals` lists every offending image, and nothing was resolved."""

    def __init__(self, refusals: Sequence[ManifestRefusal]) -> None:
        self.refusals: list[ManifestRefusal] = list(refusals)
        lines = [f"manifest resolution refused {len(self.refusals)} image(s); nothing is sent"]
        lines.extend(f"{refusal.file_name}: {refusal.reason}" for refusal in self.refusals)
        super().__init__("\n".join(lines))


class _Refused(Exception):
    """One image's refusal, raised inside its resolution and collected by the caller."""


def _jumbf_sidecar_part(sidecar: SidecarManifest) -> ManifestPart:
    """Walk and classify a JUMBF sidecar into its part; a walk failure refuses naming the sidecar."""
    try:
        read_store(sidecar.data)
        kind = classify_store(sidecar.data)
    except JumbfError as exc:
        raise _Refused(f"JUMBF sidecar {sidecar.name!r} is not well-formed JUMBF: {exc}") from exc
    return jumbf_part(kind, sidecar.data)


def _embedded_parts(image: ImageUpload) -> list[ManifestPart]:
    """The image's embedded stores as parts, document order; a malformed store or unknown carrier refuses."""
    detected = detect_embedded_c2pa(image.data)
    if detected.outcome is EmbeddedC2paOutcome.UNSUPPORTED:
        raise _Refused(f"whether the image holds an embedded manifest store cannot be said: {detected.detail}")
    if detected.outcome is EmbeddedC2paOutcome.MALFORMED:
        raise _Refused(f"the embedded manifest store is refused: {detected.detail}")
    return [jumbf_part(store.kind, store.data) for store in detected.stores]


def _require_equal_sets(sidecars: list[tuple[SidecarManifest, ManifestPart]], embedded: list[ManifestPart]) -> None:
    """Refuse unless every JUMBF sidecar matches an embedded store byte for byte, and every store a sidecar."""
    embedded_bytes = {part.data for part in embedded}
    for sidecar, _ in sidecars:
        if sidecar.data not in embedded_bytes:
            raise _Refused(f"JUMBF sidecar {sidecar.name!r} matches no manifest store embedded in the image")
    sidecar_bytes = {sidecar.data for sidecar, _ in sidecars}
    for index, part in enumerate(embedded, start=1):
        if part.data not in sidecar_bytes:
            raise _Refused(f"embedded {part.kind} manifest store {index} of {len(embedded)} matches no JUMBF sidecar")


def _resolve(image: ImageUpload, selection: ManifestSelection) -> list[ManifestPart]:
    """Resolve one image's parts: sidecars in the given order, then embedded stores not already included."""
    parts: list[ManifestPart] = []
    jumbf_sidecars: list[tuple[SidecarManifest, ManifestPart]] = []
    for sidecar in selection.sidecars:
        if sidecar.form is ManifestForm.JSON and sidecar.kind is not None:
            parts.append(ManifestPart(sidecar.kind, ManifestForm.JSON, sidecar.data))
            continue
        part = _jumbf_sidecar_part(sidecar)
        if all(included.data != part.data for _, included in jumbf_sidecars):
            parts.append(part)
        jumbf_sidecars.append((sidecar, part))
    if selection.include_embedded or jumbf_sidecars:
        embedded = _embedded_parts(image)
        if embedded and jumbf_sidecars:
            _require_equal_sets(jumbf_sidecars, embedded)
        if selection.include_embedded:
            included = {part.data for _, part in jumbf_sidecars}
            parts.extend(part for part in embedded if part.data not in included)
    for kind, count in Counter(part.kind for part in parts).items():
        if count > 1:
            raise _Refused(f"{count} manifests are of kind {kind!r}; one kind carries one manifest")
    return parts


def resolve_image_manifests(image: ImageUpload, selection: ManifestSelection) -> list[ManifestPart]:
    """Resolve one image's manifests by the selection and the conflict rule; raises `ManifestRefusalError`."""
    try:
        return _resolve(image, selection)
    except _Refused as refused:
        raise ManifestRefusalError([ManifestRefusal(image.file_name, str(refused))]) from None


def resolve_manifests(requests: Sequence[ManifestRequest]) -> list[RegistrationItem]:
    """Resolve every request before anything is sent: one `RegistrationItem` per request, in order.

    Every request is evaluated; if any refuses, `ManifestRefusalError` lists every refused image (one
    reason each) and nothing is returned.
    """
    items: list[RegistrationItem] = []
    refusals: list[ManifestRefusal] = []
    for request in requests:
        try:
            items.append(RegistrationItem(image=request.image, manifests=_resolve(request.image, request.selection)))
        except _Refused as refused:
            refusals.append(ManifestRefusal(request.image.file_name, str(refused)))
    if refusals:
        raise ManifestRefusalError(refusals)
    return items
