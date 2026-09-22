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

Run from the repository root: uv run python examples/python/register_batch.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from xio_parallax_client import (
    ImageUpload,
    LookupBatchOptions,
    ParallaxClient,
    ParallaxClientOptions,
    RegisterBatchOptions,
    RegistrationItem,
    UploadBatching,
)
from xio_parallax_client.generated.models import SlotProgressResponse


def required(name: str) -> str:
    """Reads one required environment variable or exits naming it."""
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set")
    return value


def main() -> None:
    """Registers every file in the folder, then looks every one of them up."""
    content_type = required("PARALLAX_IMAGE_TYPE")
    folder = Path(required("PARALLAX_IMAGES"))
    images = [ImageUpload.from_file(p, content_type) for p in sorted(folder.iterdir()) if p.is_file()]
    if not images:
        sys.exit(f"no files under {folder}")

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
        [RegistrationItem(image=image) for image in images],
        RegisterBatchOptions(poll_interval=1.0, poll_timeout=300.0, existing_slot_id=os.environ.get("PARALLAX_SLOT_ID")),
        on_progress=progress,
    )
    print("slot", registered.slot_id, "committed;", len(registered.upload_outcomes), "uploads this run")
    for entry in registered.final_progress.entries:
        print(f"  {entry.image_hash}: {entry.state} {entry.registration_id or entry.failure_reason or ''}")

    found = client.lookup_batch(images, LookupBatchOptions(poll_interval=1.0, poll_timeout=300.0))
    print("lookup slot", found.lookup_slot_id)
    for query in found.results.queries:
        matched = query.result.matched if query.result else None
        print(f"  {query.image_hash}: {query.state} matched={matched}")


if __name__ == "__main__":
    main()
