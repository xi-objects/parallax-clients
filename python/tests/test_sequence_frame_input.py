"""PC-111: SequenceFrameInput's validation, mirroring .NET's SequenceFrameInput, every offence named."""

from __future__ import annotations

from datetime import timedelta

import pytest
from xio_parallax_client.frames.protocol import PxBucketContent
from xio_parallax_client.frames.source import SequenceFrameInput


def _bucket(tag: str = "IMAG") -> PxBucketContent:
    return PxBucketContent(tag, b"bytes")


def test_a_valid_frame_holds_its_fields() -> None:
    frame = SequenceFrameInput(1, timedelta(seconds=1), (_bucket(),))
    assert frame.frame_id == 1
    assert frame.source_time_offset == timedelta(seconds=1)
    assert frame.buckets == (_bucket(),)


def test_for_image_builds_a_single_image_bucket_frame() -> None:
    frame = SequenceFrameInput.for_image(2, timedelta(0), b"image-bytes")
    assert frame.buckets == (PxBucketContent("IMAG", b"image-bytes"),)


def test_refuses_a_frame_id_of_zero_naming_it() -> None:
    with pytest.raises(ValueError, match="frame_id must be above zero; was 0"):
        SequenceFrameInput(0, timedelta(0), (_bucket(),))


def test_refuses_a_negative_frame_id_naming_it() -> None:
    with pytest.raises(ValueError, match=r"frame_id must be above zero; was -1"):
        SequenceFrameInput(-1, timedelta(0), (_bucket(),))


def test_refuses_a_negative_source_time_offset() -> None:
    with pytest.raises(ValueError, match="source_time_offset must not be negative"):
        SequenceFrameInput(1, timedelta(microseconds=-1), (_bucket(),))


def test_refuses_no_bucket() -> None:
    with pytest.raises(ValueError, match="a frame needs at least one bucket"):
        SequenceFrameInput(1, timedelta(0), ())


def test_refuses_a_repeated_tag_naming_it() -> None:
    with pytest.raises(ValueError, match=r"a frame's buckets repeat tag 'IMAG'"):
        SequenceFrameInput(1, timedelta(0), (_bucket("IMAG"), _bucket("IMAG")))


def test_lists_every_offence_at_once() -> None:
    with pytest.raises(ValueError) as excinfo:
        SequenceFrameInput(0, timedelta(microseconds=-1), ())
    message = str(excinfo.value)
    assert "frame_id" in message
    assert "source_time_offset" in message
    assert "at least one bucket" in message


# PC-111: rework - a bad bucket is refused by input validation, before any send, naming the tag
@pytest.mark.parametrize("tag", ["IMG", "IMAGE", "im g", ""])
def test_refuses_a_tag_not_exactly_4_bytes_in_0x21_0x7e(tag: str) -> None:
    with pytest.raises(ValueError, match=r"bucket tag .* must be exactly 4 bytes in 0x21-0x7E"):
        SequenceFrameInput(1, timedelta(0), (_bucket(tag),))


# PC-111: rework - empty bucket data is refused by input validation, naming the offending bucket
def test_refuses_empty_bucket_data_naming_it() -> None:
    with pytest.raises(ValueError, match=r"bucket 'IMAG' has no data"):
        SequenceFrameInput(1, timedelta(0), (PxBucketContent("IMAG", b""),))


# PC-111: rework - a bad tag and empty data on the same frame are both named at once
def test_lists_a_bad_tag_and_empty_data_together() -> None:
    with pytest.raises(ValueError) as excinfo:
        SequenceFrameInput(1, timedelta(0), (PxBucketContent("bad", b""),))
    message = str(excinfo.value)
    assert "must be exactly 4 bytes" in message
    assert "has no data" in message
