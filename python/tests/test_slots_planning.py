"""Pure decision logic shared by both clients: batch planning, terminal-state and backoff."""

from __future__ import annotations

import pytest
from xio_parallax_client import LookupBatchOptions, RegisterBatchOptions
from xio_parallax_client.generated.models.slot_progress_counts import SlotProgressCounts
from xio_parallax_client.generated.models.slot_progress_entry_response import SlotProgressEntryResponse
from xio_parallax_client.generated.models.slot_progress_response import SlotProgressResponse
from xio_parallax_client.options import UploadBatching
from xio_parallax_client.slots import is_progress_terminal, next_poll_delay, plan_batches


def _sizes(mapping: dict[str, int]):
    return lambda h: mapping[h]


def test_plan_batches_splits_on_image_count_cap() -> None:
    batching = UploadBatching(max_request_bytes=1_000_000, max_images_per_request=2)
    hashes = ["a", "b", "c", "d", "e"]
    batches = plan_batches(hashes, _sizes({h: 10 for h in hashes}), batching)
    assert batches == [["a", "b"], ["c", "d"], ["e"]]


def test_plan_batches_splits_on_byte_cap() -> None:
    batching = UploadBatching(max_request_bytes=25, max_images_per_request=100)
    sizes = {"a": 10, "b": 10, "c": 10}
    batches = plan_batches(["a", "b", "c"], _sizes(sizes), batching)
    assert batches == [["a", "b"], ["c"]]


def test_plan_batches_keeps_an_oversized_single_item_alone() -> None:
    batching = UploadBatching(max_request_bytes=5, max_images_per_request=100)
    sizes = {"a": 50}
    batches = plan_batches(["a"], _sizes(sizes), batching)
    assert batches == [["a"]]


def test_plan_batches_empty_input() -> None:
    batching = UploadBatching(max_request_bytes=100, max_images_per_request=10)
    assert plan_batches([], _sizes({}), batching) == []


def _progress(states: list[str]) -> SlotProgressResponse:
    entries = [
        SlotProgressEntryResponse(image_hash=f"h{i}", state=state, registration_id=None, failure_reason=None)
        for i, state in enumerate(states)
    ]
    counts = SlotProgressCounts(total=len(states), held=0, registered=0, answered=0, failed=0, errata=0, retry=0)
    return SlotProgressResponse(slot_id="slot-1", status="committed", counts=counts, entries=entries)


def test_is_progress_terminal_false_while_any_entry_is_retry() -> None:
    assert not is_progress_terminal(_progress(["registered", "retry"]))


def test_is_progress_terminal_true_with_no_retry_entries() -> None:
    assert is_progress_terminal(_progress(["registered", "errata", "failed"]))


def test_is_progress_terminal_true_for_empty_entries() -> None:
    assert is_progress_terminal(_progress([]))


def test_next_poll_delay_doubles_and_caps() -> None:
    assert next_poll_delay(1.0, cap=10.0) == 2.0
    assert next_poll_delay(8.0, cap=10.0) == 10.0
    assert next_poll_delay(20.0, cap=10.0) == 10.0


def test_blank_existing_slot_id_is_refused() -> None:
    """A present-but-blank slot id is a refusal, never a request to /slots//uploads/missing."""
    with pytest.raises(ValueError, match="existing_slot_id is blank"):
        RegisterBatchOptions(poll_interval=1.0, poll_timeout=10.0, existing_slot_id="")
    with pytest.raises(ValueError, match="existing_lookup_slot_id is blank"):
        LookupBatchOptions(existing_lookup_slot_id="   ")
    assert RegisterBatchOptions(poll_interval=1.0, poll_timeout=10.0).existing_slot_id is None
