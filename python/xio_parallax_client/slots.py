"""The slot-conversation types and the pure decisions they need: batch planning, hashing, backoff.

`ParallaxClient.register_batch`/`lookup_batch` and their `AsyncParallaxClient` mirrors do the actual
I/O (open, upload, commit, poll); everything here is plain, synchronous, and shared between both.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from . import hashing
from .generated.models.lookup_results_response import LookupResultsResponse
from .generated.models.published_record_outcome import PublishedRecordOutcome
from .generated.models.slot_commit_response import SlotCommitResponse
from .generated.models.slot_progress_response import SlotProgressResponse
from .generated.models.slot_upload_outcome_response import SlotUploadOutcomeResponse
from .multipart import ImageUpload, ManifestPart
from .options import UploadBatching


@dataclass(frozen=True, slots=True)
class RegistrationItem:
    """One image and the manifests to attach to it, as one entry of a `register_batch` call."""

    image: ImageUpload
    manifests: Sequence[ManifestPart] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RegisterBatchOptions:
    """Options for one `register_batch` conversation.

    `poll_interval` and `poll_timeout` are required: there is no default backoff or deadline the
    client should guess. `existing_slot_id` resumes an open slot; running the same call again after
    an interruption *is* the resume, because the missing-hashes call uploads only what the slot lacks.
    """

    poll_interval: float
    poll_timeout: float
    existing_slot_id: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterBatchResult:
    """The outcome of one `register_batch` conversation."""

    slot_id: str
    commit: SlotCommitResponse
    final_progress: SlotProgressResponse
    upload_outcomes: list[SlotUploadOutcomeResponse]


@dataclass(frozen=True, slots=True)
class LookupBatchOptions:
    """Options for one `lookup_batch` conversation; mirrors `RegisterBatchOptions`."""

    poll_interval: float
    poll_timeout: float
    existing_lookup_slot_id: str | None = None


@dataclass(frozen=True, slots=True)
class LookupBatchResult:
    """The outcome of one `lookup_batch` conversation."""

    lookup_slot_id: str
    results: LookupResultsResponse
    final_progress: SlotProgressResponse


@dataclass(frozen=True, slots=True)
class RecordWaitOptions:
    """Options for `wait_for_record`; both fields are required, mirroring `RegisterBatchOptions`.

    A record is published some seconds after registration, so there is no default backoff or
    deadline the client should guess.
    """

    poll_interval: float
    poll_timeout: float


def hash_registration_items(items: Sequence[RegistrationItem]) -> dict[str, RegistrationItem]:
    """Map each item's image bytes to its lowercase SHA-256 hex hash."""
    return {hashing.sha256_hex(item.image.data): item for item in items}


def hash_images(images: Sequence[ImageUpload]) -> dict[str, ImageUpload]:
    """Map each image's bytes to its lowercase SHA-256 hex hash."""
    return {hashing.sha256_hex(image.data): image for image in images}


def plan_batches(hashes: Sequence[str], byte_size_of: Callable[[str], int], batching: UploadBatching) -> list[list[str]]:
    """Group `hashes` into upload batches, each under `batching`'s byte and image-count caps.

    A single item whose own size already exceeds `max_request_bytes` still forms its own one-item
    batch; the server is left to refuse it rather than the client silently splitting an image.
    """
    batches: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for image_hash in hashes:
        size = byte_size_of(image_hash)
        would_overflow_count = len(current) >= batching.max_images_per_request
        would_overflow_bytes = current and current_bytes + size > batching.max_request_bytes
        if current and (would_overflow_count or would_overflow_bytes):
            batches.append(current)
            current = []
            current_bytes = 0
        current.append(image_hash)
        current_bytes += size
    if current:
        batches.append(current)
    return batches


def plan_registration_batches(
    missing_hashes: Sequence[str], hash_to_item: Mapping[str, RegistrationItem], batching: UploadBatching
) -> list[list[str]]:
    """Group missing registration hashes into upload batches, sized by each item's manifests plus image."""

    def size_of(image_hash: str) -> int:
        item = hash_to_item[image_hash]
        return len(item.image.data) + sum(len(manifest.data) for manifest in item.manifests)

    return plan_batches(missing_hashes, size_of, batching)


def plan_lookup_batches(
    missing_hashes: Sequence[str], hash_to_image: Mapping[str, ImageUpload], batching: UploadBatching
) -> list[list[str]]:
    """Group missing look-up hashes into upload batches, sized by each image alone."""

    def size_of(image_hash: str) -> int:
        return len(hash_to_image[image_hash].data)

    return plan_batches(missing_hashes, size_of, batching)


def is_progress_terminal(progress: SlotProgressResponse) -> bool:
    """Return `True` once no entry in `progress` is still `retry` (the engine has answered all of them)."""
    return all(entry.state != "retry" for entry in progress.entries)


def is_record_outcome_terminal(outcome: PublishedRecordOutcome) -> bool:
    """Return `True` for `published`, `takenDown` or `refused`; `False` for `noRecordAnswered`/`retry`."""
    return outcome not in (PublishedRecordOutcome.NORECORDANSWERED, PublishedRecordOutcome.RETRY)


def next_poll_delay(current: float, cap: float) -> float:
    """The next exponential-backoff delay: double `current`, capped at `cap`."""
    return min(current * 2, cap)
