"""Shared, hand-written plumbing used by both `ParallaxClient` and `AsyncParallaxClient`.

These helpers hold no client state of their own; each is called with `self.options` or `self.api`
passed in explicitly, which is what lets `client.py` and `async_client.py` share them.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from . import problems
from .generated.client import AuthenticatedClient
from .generated.models import PublishedRecordOutcome, PublishedRecordResponse, SlotProgressResponse
from .options import ParallaxClientOptions
from .slots import (
    RecordWaitOptions,
    RegisterBatchOptions,
    is_progress_terminal,
    is_record_outcome_terminal,
    next_poll_delay,
)

ProgressCallback = Callable[[SlotProgressResponse], None]

T = TypeVar("T")


def _build_api(options: ParallaxClientOptions) -> AuthenticatedClient:
    """Construct the generated `AuthenticatedClient`, with the admin key as an extra header when set."""
    headers: dict[str, str] = {}
    if options.admin_key is not None:
        headers["X-Admin-Key"] = options.admin_key
    return AuthenticatedClient(base_url=options.base_url, token=options.account_token or "", headers=headers)


def _parsed(response: Any) -> Any:
    """Return `response.parsed`, populated for every documented 2xx status this layer calls."""
    if response.parsed is None:
        raise problems.ParallaxClientError("the server returned an empty body for a documented success status")
    return response.parsed


def _require_batching(options: ParallaxClientOptions, call_name: str) -> Any:
    """Return `options.batching`, or raise since a batch call never guesses the server's caps."""
    if options.batching is None:
        raise problems.ParallaxClientError(
            f"{call_name} requires ParallaxClientOptions.batching (max_request_bytes, "
            "max_images_per_request); the server's caps are operator configuration and are never guessed."
        )
    return options.batching


def _record_wait_timeout(
    original_image_hash: str, elapsed: float, options: RecordWaitOptions, outcome: PublishedRecordOutcome
) -> problems.ParallaxClientError:
    """Build the `ParallaxClientError` `wait_for_record` raises on timeout, naming the hash and last outcome."""
    return problems.ParallaxClientError(
        f"waiting for the record of {original_image_hash!r} timed out after {elapsed:.3f}s "
        f"(poll_timeout={options.poll_timeout}s); last outcome was '{outcome}'"
    )


def _poll_for_record(
    get_record: Callable[[str], PublishedRecordResponse], original_image_hash: str, options: RecordWaitOptions
) -> PublishedRecordResponse:
    """Shared body of `ParallaxClient.wait_for_record`: poll `get_record` until the outcome is terminal.

    `noRecordAnswered`/`retry` are retried with the same bounded exponential backoff
    `register_batch`/`lookup_batch` poll with; raises once `options.poll_timeout` elapses.
    """
    delay = options.poll_interval
    elapsed = 0.0
    while True:
        record = get_record(original_image_hash)
        if is_record_outcome_terminal(record.outcome):
            return record
        if elapsed >= options.poll_timeout:
            raise _record_wait_timeout(original_image_hash, elapsed, options, record.outcome)
        wait = min(delay, options.poll_timeout - elapsed)
        time.sleep(wait)
        elapsed += wait
        delay = next_poll_delay(delay, options.poll_timeout)


async def _poll_for_record_async(
    get_record: Callable[[str], Awaitable[PublishedRecordResponse]],
    original_image_hash: str,
    options: RecordWaitOptions,
) -> PublishedRecordResponse:
    """Async mirror of `_poll_for_record`, the shared body of `AsyncParallaxClient.wait_for_record`."""
    delay = options.poll_interval
    elapsed = 0.0
    while True:
        record = await get_record(original_image_hash)
        if is_record_outcome_terminal(record.outcome):
            return record
        if elapsed >= options.poll_timeout:
            raise _record_wait_timeout(original_image_hash, elapsed, options, record.outcome)
        wait = min(delay, options.poll_timeout - elapsed)
        await asyncio.sleep(wait)
        elapsed += wait
        delay = next_poll_delay(delay, options.poll_timeout)


# PC-113: moved from ParallaxClient._poll_progress so client.py stays under 300 lines
def _poll_slot_progress(
    fetch: Callable[[], Any],
    options: RegisterBatchOptions,
    on_progress: ProgressCallback | None,
) -> SlotProgressResponse:
    """Shared body of `ParallaxClient.register_batch`'s poll: poll `fetch` until no entry is `retry`.

    Raises `ParallaxClientError` once `options.poll_timeout` elapses with entries still `retry`.
    """
    delay = options.poll_interval
    elapsed = 0.0
    while True:
        response = fetch()
        problems.raise_for_problem(response)
        progress = _parsed(response)
        if on_progress is not None:
            on_progress(progress)
        if is_progress_terminal(progress):
            return progress
        if elapsed >= options.poll_timeout:
            raise problems.ParallaxClientError(
                f"polling timed out after {elapsed:.3f}s (poll_timeout={options.poll_timeout}s) "
                "with entries still in state 'retry'"
            )
        wait = min(delay, options.poll_timeout - elapsed)
        time.sleep(wait)
        elapsed += wait
        delay = next_poll_delay(delay, options.poll_timeout)


# PC-113: async mirror of `_poll_slot_progress`, for `AsyncParallaxClient.register_batch`
async def _poll_slot_progress_async(
    fetch: Callable[[], Awaitable[Any]],
    options: RegisterBatchOptions,
    on_progress: ProgressCallback | None,
) -> SlotProgressResponse:
    """Async mirror of `_poll_slot_progress`."""
    delay = options.poll_interval
    elapsed = 0.0
    while True:
        response = await fetch()
        problems.raise_for_problem(response)
        progress = _parsed(response)
        if on_progress is not None:
            on_progress(progress)
        if is_progress_terminal(progress):
            return progress
        if elapsed >= options.poll_timeout:
            raise problems.ParallaxClientError(
                f"polling timed out after {elapsed:.3f}s (poll_timeout={options.poll_timeout}s) "
                "with entries still in state 'retry'"
            )
        wait = min(delay, options.poll_timeout - elapsed)
        await asyncio.sleep(wait)
        elapsed += wait
        delay = next_poll_delay(delay, options.poll_timeout)
