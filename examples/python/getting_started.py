"""The API docs' getting-started walk, with the client: token check, health, register, find,
recover the record, verify it, take it down.

Environment:
  PARALLAX_BASE_URL       the API's base URL (defaults to https://api.parallax.xiobjects.com)
  PARALLAX_TOKEN          the account token that registers (required)
  PARALLAX_LOOKUP_TOKEN   a second account's token that looks the image up (defaults to PARALLAX_TOKEN)
  PARALLAX_IMAGE          path of the image to register (required)
  PARALLAX_IMAGE_TYPE     its media type, for example image/png (required)
  PARALLAX_MANIFEST       optional path of a JSON manifest to attach under the kind xi-manifest
  PARALLAX_ORBITAL_URL    Orbital's base URL, whose anonymous /info serves the pinned roots
  PARALLAX_ROOTS_PEM      or a PEM file holding the pinned roots (one of the two is required)

Run from the repository root: uv run python examples/python/getting_started.py
"""

from __future__ import annotations

import os
import sys

from xio_parallax_client import (
    ImageUpload,
    ManifestForm,
    ManifestPart,
    ParallaxClient,
    ParallaxClientOptions,
    ParallaxProblem,
    RecordWaitOptions,
)
from xio_parallax_client.verification import AttributionVerifier, TrustRoots


def required(name: str) -> str:
    """Reads one required environment variable or exits naming it."""
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set")
    return value


def trust_roots() -> TrustRoots:
    """The pinned roots, from Orbital's /info or from a PEM file; never a default."""
    orbital = os.environ.get("PARALLAX_ORBITAL_URL")
    pem = os.environ.get("PARALLAX_ROOTS_PEM")
    if orbital:
        return TrustRoots.from_orbital(orbital)
    if pem:
        return TrustRoots.from_pem_file(pem)
    sys.exit("set PARALLAX_ORBITAL_URL or PARALLAX_ROOTS_PEM")


def main() -> None:
    """Walks the sequence and prints each step's outcome."""
    token = required("PARALLAX_TOKEN")
    image = ImageUpload.from_file(required("PARALLAX_IMAGE"), required("PARALLAX_IMAGE_TYPE"))
    manifests: list[ManifestPart] = []
    manifest_path = os.environ.get("PARALLAX_MANIFEST")
    if manifest_path:
        with open(manifest_path, "rb") as f:
            manifests.append(ManifestPart(kind="xi-manifest", form=ManifestForm.JSON, data=f.read()))

    base_url = os.environ.get("PARALLAX_BASE_URL") or ParallaxClientOptions().base_url
    registrant = ParallaxClient(ParallaxClientOptions(account_token=token, base_url=base_url))
    finder = ParallaxClient(
        ParallaxClientOptions(account_token=os.environ.get("PARALLAX_LOOKUP_TOKEN") or token, base_url=base_url)
    )

    stats = registrant.account_stats()
    print("token ok; stats:", stats.to_dict())
    print("health:", registrant.health().to_dict())

    try:
        registered = registrant.register(image, manifests)
    except ParallaxProblem as problem:
        sys.exit(f"register refused: {problem.status} {problem.slug}: {problem.detail}")
    print(
        "registered:", registered.id,
        "image hash:", registered.image_hash,
        "original image hash:", registered.original_image_hash,
    )
    if registered.original_image_hash is None:
        sys.exit("register did not return an original image hash; there is no record to recover")

    found = finder.lookup(image)
    print("lookup matched:", found.matched, "hashes:", found.matched_original_image_hashes)

    # Publication follows registration by some seconds; wait_for_record polls (bounded exponential
    # backoff) instead of a single get_record that could still answer noRecordAnswered.
    record = finder.wait_for_record(
        registered.original_image_hash, RecordWaitOptions(poll_interval=2.0, poll_timeout=120.0)
    )
    print("record outcome:", record.outcome)

    report = AttributionVerifier(trust_roots()).verify(record, original_image_bytes=image.data)
    for check in report.checks:
        print(f"  {check.name}: {check.outcome.name} {check.detail}")
    print("all performed checks passed:", report.all_performed_passed)

    registrant.unregister(str(registered.id))
    print("taken down:", registered.id)


if __name__ == "__main__":
    main()
