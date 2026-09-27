"""The frame source seam: what a later ingestion implements to hand the client a sequence's frames.

Mirrors the .NET client's `ISequenceFrameSource`. A source yields `SequenceFrameInput`s in chain
order. It owns each frame's id (monotone, room between ids allowed) and its position within its
own media, and says nothing about the links between frames: the client derives every frame's prev
from the frame read immediately before it (the sequence's HEAD id for the first) and its next from
the frame read immediately after it (the END id for the last), buffering one frame of lookahead.
"""

# PC-111: the frame source contract a later ingestion implements

from __future__ import annotations

from collections.abc import AsyncIterable, Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol, runtime_checkable

from .protocol import IMAGE_BUCKET_TAG, PxBucketContent

# PC-111: rework - the format's bucket-tag shape, checked here (input validation) as well as by the
# encoder; kept local to source.py rather than imported from frames.pure, which only binding.py may
# import (see test_only_binding_imports_the_pure_codec)
_BUCKET_TAG_LENGTH = 4
_MIN_BUCKET_TAG_BYTE = 0x21
_MAX_BUCKET_TAG_BYTE = 0x7E


def _is_valid_bucket_tag(tag: str) -> bool:
    """A bucket tag is exactly four characters, each in 0x21-0x7E."""
    return len(tag) == _BUCKET_TAG_LENGTH and all(
        _MIN_BUCKET_TAG_BYTE <= ord(character) <= _MAX_BUCKET_TAG_BYTE for character in tag
    )


@dataclass(frozen=True, slots=True)
class SequenceFrameInput:
    """One frame a source hands the client: its id, its position within its own media, its buckets.

    `frame_id` is above zero and monotone along the chain; `source_time_offset` is not negative
    and is carried on the wire in whole microseconds; `buckets` is non-empty, in table order, with
    no repeated tag. The source owns `frame_id` but says nothing about prev or next. Every bad
    field is named together in one `ValueError`, raised before any request.
    """

    frame_id: int
    source_time_offset: timedelta
    buckets: tuple[PxBucketContent, ...]

    # PC-111: rework - also refuses a malformed tag or empty data, naming every offending bucket,
    # so a bad frame is caught before any send rather than by the encoder mid-stream (PC-112)
    def __post_init__(self) -> None:
        """Refuse a non-positive id, a negative offset, no bucket, a repeated or malformed tag, or
        empty bucket data; name every one together."""
        errors: list[str] = []
        if self.frame_id <= 0:
            errors.append(f"frame_id must be above zero; was {self.frame_id}")
        if self.source_time_offset < timedelta(0):
            errors.append(f"source_time_offset must not be negative; was {self.source_time_offset}")
        if not self.buckets:
            errors.append("a frame needs at least one bucket")
        else:
            seen: set[str] = set()
            duplicates: set[str] = set()
            for bucket in self.buckets:
                if not _is_valid_bucket_tag(bucket.tag):
                    errors.append(f"bucket tag {bucket.tag!r} must be exactly 4 bytes in 0x21-0x7E")
                elif bucket.tag in seen:
                    duplicates.add(bucket.tag)
                seen.add(bucket.tag)
                if not bucket.data:
                    errors.append(f"bucket {bucket.tag!r} has no data")
            for tag in sorted(duplicates):
                errors.append(f"a frame's buckets repeat tag {tag!r}")
        if errors:
            raise ValueError("; ".join(errors))

    @classmethod
    def for_image(cls, frame_id: int, source_time_offset: timedelta, image_bytes: bytes) -> SequenceFrameInput:
        """Build a frame carrying a single image bucket, under the format's declared image tag."""
        return cls(frame_id, source_time_offset, (PxBucketContent(IMAGE_BUCKET_TAG, image_bytes),))


@runtime_checkable
class SequenceFrameSource(Protocol):
    """A synchronous source of one sequence's frames, in chain order; `ParallaxClient` reads it."""

    def read_frames(self) -> Iterable[SequenceFrameInput]:
        """Yield the source's frames, in chain order; read again from the start on every call."""
        ...


@runtime_checkable
class AsyncSequenceFrameSource(Protocol):
    """An asynchronous source of one sequence's frames, in chain order; `AsyncParallaxClient` reads it
    (it reads a `SequenceFrameSource` too)."""

    def read_frames_async(self) -> AsyncIterable[SequenceFrameInput]:
        """Yield the source's frames, in chain order; read again from the start on every call."""
        ...
