"""Registers a whole folder of images through one slot conversation, then looks them all up in
one look-up slot conversation. Re-running the same command after an interruption resumes: the
client re-declares every hash and uploads only what the slot does not already hold.

Environment:
  PARALLAX_BASE_URL           the API's base URL (defaults to https://api.parallax.xiobjects.com)
  PARALLAX_TOKEN              the account token (required)
  PARALLAX_IMAGES             a folder of images (required)
  PARALLAX_IMAGE_TYPE         their media type, for example image/jpeg (required)
  PARALLAX_MAX_REQUEST_BYTES  the operator's per-request byte cap (required; not in the document)
  PARALLAX_MAX_IMAGES         the operator's per-request image cap (required)
  PARALLAX_SLOT_ID            optional: an open slot to resume into instead of opening a new one
  PARALLAX_INCLUDE_EMBEDDED   "yes" to include each image's embedded JUMBF manifest store(s)

Each image's manifests are what you choose: `<image>.json` beside the file is a JSON sidecar sent as
manifest[xi-manifest]; `<image>.c2pa` or `<image>.jumbf` beside it is a JUMBF sidecar whose kind
(`c2pa` or `jumbf`) is classified from its own bytes; the embedded store(s) are included only when
asked. The whole folder is resolved before anything is sent: a JUMBF sidecar that differs from the
image's embedded store, a malformed store, an unrecognised carrier where the embedded store matters,
or two manifests of one kind refuses the whole run, every offending image listed.

Run from the repository root: uv run python examples/python/register_batch.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from xio_parallax_client import (
    ImageUpload,
    LookupBatchOptions,
    ManifestRefusalError,
    ManifestRequest,
    ManifestSelection,
    ParallaxClient,
    ParallaxClientOptions,
    RegisterBatchOptions,
    SidecarManifest,
    UploadBatching,
    resolve_manifests,
)
from xio_parallax_client.generated.models import SlotProgressResponse


def required(name: str) -> str:
    """Reads one required environment variable or exits naming it."""
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set")
    return value


_JSON_SUFFIX = ".json"
_JUMBF_SUFFIXES = (".c2pa", ".jumbf")
_SIDECAR_SUFFIXES = (_JSON_SUFFIX, *_JUMBF_SUFFIXES)


def selection_for(path: Path, include_embedded: bool) -> ManifestSelection:
    """The manifests chosen for one image: the sidecars beside it, and its embedded store(s) on request."""
    sidecars: list[SidecarManifest] = []
    json_sidecar = path.with_suffix(path.suffix + _JSON_SUFFIX)
    if json_sidecar.is_file():
        sidecars.append(SidecarManifest.json_file(json_sidecar, "xi-manifest"))
    for suffix in _JUMBF_SUFFIXES:
        jumbf_sidecar = path.with_suffix(path.suffix + suffix)
        if jumbf_sidecar.is_file():
            sidecars.append(SidecarManifest.jumbf_file(jumbf_sidecar))
    return ManifestSelection(include_embedded=include_embedded, sidecars=sidecars)


def main() -> None:
    """Resolves every image's manifests, registers them all if none refused, then looks every one of them up."""
    content_type = required("PARALLAX_IMAGE_TYPE")
    folder = Path(required("PARALLAX_IMAGES"))
    include_embedded = os.environ.get("PARALLAX_INCLUDE_EMBEDDED", "").lower() == "yes"
    paths = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() not in _SIDECAR_SUFFIXES]
    images = [ImageUpload.from_file(p, content_type) for p in paths]
    if not images:
        sys.exit(f"no images under {folder}")
    requests = [ManifestRequest(image, selection_for(p, include_embedded)) for p, image in zip(paths, images)]
    try:
        items = resolve_manifests(requests)
    except ManifestRefusalError as refused:
        print(f"refused {len(refused.refusals)} image(s); nothing was sent:", file=sys.stderr)
        for refusal in refused.refusals:
            print(f"  {refusal.file_name}: {refusal.reason}", file=sys.stderr)
        sys.exit(1)
    for item in items:
        print(f"  {item.image.file_name}: {[m.kind for m in item.manifests] or 'no manifests'}")

    client = ParallaxClient(
        ParallaxClientOptions(
            base_url=os.environ.get("PARALLAX_BASE_URL") or ParallaxClientOptions().base_url,
            account_token=required("PARALLAX_TOKEN"),
            batching=UploadBatching(
                max_request_bytes=int(required("PARALLAX_MAX_REQUEST_BYTES")),
                max_images_per_request=int(required("PARALLAX_MAX_IMAGES")),
            ),
        )
    )

    def progress(p: SlotProgressResponse) -> None:
        counts = p.counts
        print(f"  progress: registered={counts.registered} failed={counts.failed} retry={counts.retry}")

    registered = client.register_batch(
        items,
        RegisterBatchOptions(
            poll_interval=1.0, poll_timeout=300.0, existing_slot_id=os.environ.get("PARALLAX_SLOT_ID") or None
        ),
        on_progress=progress,
    )
    print("slot", registered.slot_id, "committed;", len(registered.upload_outcomes), "uploads this run")
    for entry in registered.final_progress.entries:
        print(f"  {entry.image_hash}: {entry.state} {entry.registration_id or entry.failure_reason or ''}")

    found = client.lookup_batch(images, LookupBatchOptions())
    print("lookup slot", found.lookup_slot_id)
    for query in found.results.queries:
        matched = query.result.matched if query.result else None
        print(f"  {query.image_hash}: {query.state} matched={matched}")


if __name__ == "__main__":
    main()
