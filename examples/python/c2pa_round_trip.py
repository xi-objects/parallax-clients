"""Detects the C2PA manifest store embedded in an image, shows it, attaches it explicitly on
registration, then plays the finder: extracts the store from the file again and compares it with
the recovered record.

Environment:
  PARALLAX_BASE_URL              the API's base URL (defaults to https://api.parallax.xiobjects.com)
  PARALLAX_TOKEN                 the account token (required)
  PARALLAX_IMAGE                 path of the image (required); JPEG, PNG, WebP or TIFF carriers
  PARALLAX_IMAGE_TYPE            its media type (required)
  PARALLAX_ATTACH_EMBEDDED_C2PA  "yes" to attach the detected store as manifest[c2pa]; anything
                                 else registers without it (the registrant decides, never the client)

Run from the repository root: uv run python examples/python/c2pa_round_trip.py
"""

from __future__ import annotations

import os
import sys

from xio_parallax_client import (
    C2paCarrier,
    ImageUpload,
    ParallaxClient,
    ParallaxClientOptions,
    RecordWaitOptions,
    as_manifest_part,
    compare_with_record,
    detect_embedded_c2pa,
)


def required(name: str) -> str:
    """Reads one required environment variable or exits naming it."""
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set")
    return value


def main() -> None:
    """Detects, shows, attaches on request, registers, recovers and compares."""
    image = ImageUpload.from_file(required("PARALLAX_IMAGE"), required("PARALLAX_IMAGE_TYPE"))
    detected = detect_embedded_c2pa(image.data)
    if detected.carrier is C2paCarrier.UNSUPPORTED:
        sys.exit(f"unsupported carrier: {detected.detail}")
    if detected.store is None:
        sys.exit(f"{detected.carrier.name}: no embedded C2PA manifest store ({detected.detail})")
    print(f"{detected.carrier.name}: embedded C2PA store of {len(detected.store.data)} bytes:")
    for b in detected.store.boxes:
        print(f"  {'  ' * b.depth}{b.type} label={b.label!r} length={b.length}")

    manifests = []
    if os.environ.get("PARALLAX_ATTACH_EMBEDDED_C2PA", "").lower() == "yes":
        manifests.append(as_manifest_part(detected.store))
        print("attaching it as manifest[c2pa]")
    else:
        print("not attaching it (set PARALLAX_ATTACH_EMBEDDED_C2PA=yes to attach)")

    client = ParallaxClient(
        ParallaxClientOptions(
            account_token=required("PARALLAX_TOKEN"),
            base_url=os.environ.get("PARALLAX_BASE_URL") or ParallaxClientOptions().base_url,
        )
    )
    registered = client.register(image, manifests)
    if registered.original_image_hash is None:
        sys.exit("register did not return an original image hash; there is no record to recover")
    print("registered:", registered.id, "original image hash:", registered.original_image_hash)

    record = client.wait_for_record(
        registered.original_image_hash, RecordWaitOptions(poll_interval=2.0, poll_timeout=120.0)
    )
    print("record outcome:", record.outcome)

    # The finder's side: the same detection on the file that was found, compared with the record.
    found = detect_embedded_c2pa(image.data)
    if found.store is None:
        sys.exit("the found file carries no store to compare")
    comparison = compare_with_record(found.store, record)
    print(f"comparison: {comparison.outcome.name} kind={comparison.matched_kind!r} - {comparison.detail}")

    client.unregister(str(registered.id))
    print("taken down:", registered.id)


if __name__ == "__main__":
    main()
