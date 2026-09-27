"""Registers a directory of image files as one sequence, one frame per file, through the one-call
conversation, then looks the first image up. Mirrors `examples/dotnet/SequenceFromImages`: the
stand-in for the ingestion that later decodes a video into frames, proving `SequenceFrameSource`
is enough for a real registration.

Environment:
  PARALLAX_BASE_URL                the API's base URL (defaults to https://api.parallax.xiobjects.com)
  PARALLAX_TOKEN                   the account token (required)
  PARALLAX_IMAGES                  a directory of image files (png, jpg, jpeg, gif, webp, bmp only),
                                    read in ordinal name order (required)
  PARALLAX_FRAME_INTERVAL_MS       the constant interval, in milliseconds, between two frames'
                                    source time offsets (required)
  PARALLAX_MAX_REQUEST_BYTES       the operator's per-request byte cap (required; not in the document)
  PARALLAX_MAX_FRAMES_PER_REQUEST  the operator's per-request frame cap (required; not in the document)

Run from the repository root: uv run python examples/python/sequence_from_images.py
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from xio_parallax_client import (
    ImageUpload,
    ParallaxClient,
    ParallaxClientOptions,
    ParallaxProblem,
    SequenceBatching,
    SequenceFrameInput,
    SequenceOpenRequest,
    SequenceRegisterOptions,
    SequenceVerdictError,
)
from xio_parallax_client.generated.models.sequence_verdict_response import SequenceVerdictResponse

# PC-115: the image extensions this source admits, each with its media type; anything else is refused
_IMAGE_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def required(name: str) -> str:
    """Reads one required environment variable or exits naming it."""
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set")
    return value


def content_type_for(path: Path) -> str:
    """The media type of an admitted image file, by its extension; an unrecognised extension is refused."""
    content_type = _IMAGE_CONTENT_TYPES.get(path.suffix.lower())
    if content_type is None:
        sys.exit(f"not a recognised image extension: {path.name}")
    return content_type


# PC-115: the stand-in frame source, a directory of image files in ordinal name order
@dataclass(frozen=True, slots=True)
class DirectoryFrameSource:
    """A `SequenceFrameSource` over a directory of image files, in ordinal name order: frame ids
    1..n, each frame's source time offset the constant frame interval times its position. The
    stand-in for the ingestion that later decodes a video into frames.
    """

    paths: tuple[Path, ...]
    frame_interval: timedelta

    # PC-115: orders the directory's files once, ordinal, refusing any file whose extension is not an image's
    @classmethod
    def for_directory(cls, directory: Path, frame_interval: timedelta) -> DirectoryFrameSource:
        """Build the source over a directory's files, ordered ordinally by name. A file whose
        extension is not a recognised image extension is refused, naming every such file, rather
        than becoming a frame."""
        paths = tuple(sorted((p for p in directory.iterdir() if p.is_file()), key=lambda p: p.name))
        if not paths:
            sys.exit(f"no files under {directory}")
        unrecognised = [p.name for p in paths if p.suffix.lower() not in _IMAGE_CONTENT_TYPES]
        if unrecognised:
            sys.exit(f"not a recognised image extension: {', '.join(unrecognised)}")
        return cls(paths, frame_interval)

    @property
    def frame_count(self) -> int:
        """The directory's file count, the sequence's expected size."""
        return len(self.paths)

    @property
    def first_path(self) -> Path:
        """The first file's path, in ordinal name order, for the round-trip look-up."""
        return self.paths[0]

    # PC-115: yields each file's bytes as one image frame, ids 1..n in ordinal name order
    def read_frames(self) -> Iterable[SequenceFrameInput]:
        """Read the directory's files, in ordinal name order, as the sequence's frames."""
        for index, path in enumerate(self.paths):
            yield SequenceFrameInput.for_image(index + 1, self.frame_interval * index, path.read_bytes())


def print_verdict(verdict: SequenceVerdictResponse) -> None:
    """Prints one verdict line: state, frames received, expected size, reach, connected, gap and errata counts."""
    print(
        f"  verdict: state={verdict.state} framesReceived={verdict.frames_received} "
        f"expectedSize={verdict.expected_size} reach={verdict.reach} connected={verdict.connected} "
        f"gaps={len(verdict.gaps)} errata={len(verdict.errata)}"
    )


def main() -> None:
    """Registers the directory as one sequence, then looks its first image up."""
    directory = Path(required("PARALLAX_IMAGES"))
    frame_interval = timedelta(milliseconds=float(required("PARALLAX_FRAME_INTERVAL_MS")))
    max_request_bytes = int(required("PARALLAX_MAX_REQUEST_BYTES"))
    max_frames_per_request = int(required("PARALLAX_MAX_FRAMES_PER_REQUEST"))

    source = DirectoryFrameSource.for_directory(directory, frame_interval)

    base_url = os.environ.get("PARALLAX_BASE_URL") or ParallaxClientOptions().base_url
    client = ParallaxClient(ParallaxClientOptions(account_token=required("PARALLAX_TOKEN"), base_url=base_url))

    options = SequenceRegisterOptions(
        poll_interval=1.0,
        commit_attempts=5,
        batching=SequenceBatching(max_request_bytes, max_frames_per_request),
        open=SequenceOpenRequest((), source.frame_count),
    )

    try:
        result = client.register_sequence(source, options, print_verdict)
    except ParallaxProblem as problem:
        sys.exit(f"sequence refused: {problem.status} {problem.slug}: {problem.detail}")
    except SequenceVerdictError as refused:
        print(f"sequence not committed: {refused}", file=sys.stderr)
        for errata in refused.verdict.errata:
            print(f"  errata frame {errata.frame_id}: {errata.original_image_hash}", file=sys.stderr)
        sys.exit(1)

    print("sequence hash:", result.results.sequence_hash)
    print("outcome:", result.results.outcome)
    print("final size:", result.results.final_size)

    # PC-115: the look-up's media type comes from the source's own extension map, which admitted the file
    first_image = ImageUpload.from_file(source.first_path, content_type_for(source.first_path))
    found = client.lookup(first_image)
    print("lookup matched:", found.matched)


if __name__ == "__main__":
    main()
