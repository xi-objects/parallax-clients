"""The multipart shape the generated client cannot express: `manifest[<kind>]` parts before `image`.

The OpenAPI document declares a property literally named `manifest[<kind>]` (the server parses the
real manifest kind by splitting the part name on `[` and `]`); a generator renders that as a plain
field name and loses the kind entirely. This module builds the httpx `files` list by hand instead,
so it is sent through the reused httpx client rather than the generated multipart models.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_KIND_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

#: One httpx multipart file value: (file name or None, raw bytes, content type).
MultipartFile = tuple[str | None, bytes, str]
#: One httpx multipart part: (part name, file value). Duplicate names are valid as a list of tuples.
MultipartPart = tuple[str, MultipartFile]


def validate_manifest_kind(kind: str) -> None:
    """Raise `ValueError` unless `kind` matches `^[A-Za-z0-9._-]{1,64}$`, the server's rule for a manifest kind."""
    if not _KIND_PATTERN.match(kind):
        raise ValueError(
            f"manifest kind {kind!r} must match {_KIND_PATTERN.pattern} (1-64 characters "
            "of A-Z, a-z, 0-9, '.', '_' or '-')"
        )


class ManifestForm(Enum):
    """The form a manifest's stored bytes are carried in, and the content type that declares it."""

    JSON = "application/json"
    JUMBF = "application/jumbf"
    C2PA = "application/c2pa"

    @property
    def content_type(self) -> str:
        """The MIME content type sent on this manifest's part."""
        return self.value


@dataclass(frozen=True, slots=True)
class ManifestPart:
    """One manifest to attach to an image: its kind, its form, and its raw bytes.

    `kind` is validated against `^[A-Za-z0-9._-]{1,64}$` at construction, before anything is sent,
    since the server refuses it late otherwise.
    """

    kind: str
    form: ManifestForm
    data: bytes

    def __post_init__(self) -> None:
        validate_manifest_kind(self.kind)


@dataclass(frozen=True, slots=True)
class ImageUpload:
    """One image's bytes, ready to become an `image` multipart part."""

    file_name: str
    content_type: str
    data: bytes

    @classmethod
    def from_file(cls, path: str | Path, content_type: str) -> ImageUpload:
        """Read `path` off disk into an `ImageUpload` with the given `content_type`."""
        file_path = Path(path)
        return cls(file_name=file_path.name, content_type=content_type, data=file_path.read_bytes())


def build_registration_parts(manifests: Sequence[ManifestPart], image: ImageUpload) -> list[MultipartPart]:
    """Build the parts for one image: its manifests, named `manifest[<kind>]`, precede its `image` part."""
    parts: list[MultipartPart] = [
        (f"manifest[{manifest.kind}]", (None, manifest.data, manifest.form.content_type)) for manifest in manifests
    ]
    parts.append(("image", (image.file_name, image.data, image.content_type)))
    return parts


def build_upload_parts(items: Sequence[tuple[Sequence[ManifestPart], ImageUpload]]) -> list[MultipartPart]:
    """Build the parts for a slot upload: each image's manifests precede its own `image` part, in order."""
    parts: list[MultipartPart] = []
    for manifests, image in items:
        parts.extend(build_registration_parts(manifests, image))
    return parts


def build_lookup_parts(images: Sequence[ImageUpload]) -> list[MultipartPart]:
    """Build the parts for a look-up upload: images only, with no manifests and any part name."""
    return [("image", (image.file_name, image.data, image.content_type)) for image in images]
