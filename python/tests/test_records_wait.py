"""`wait_for_record`: poll `get_record` until its outcome is terminal, or time out naming the hash."""

from __future__ import annotations

import httpx
import pytest
import respx
from xio_parallax_client import AsyncParallaxClient, ParallaxClient, ParallaxClientOptions, RecordWaitOptions
from xio_parallax_client.problems import ParallaxClientError

from .conftest import BASE_URL

HASH = "abc123"


def _record_response(outcome: str) -> httpx.Response:
    """One `GET /records/{hash}` 200 response, its outcome the only thing that varies per test."""
    return httpx.Response(
        200,
        json={
            "originalImageHash": HASH,
            "outcome": outcome,
            "manifests": None,
            "verification": None,
            "failureReason": None,
        },
    )


@respx.mock
def test_wait_for_record_returns_on_first_published(options: ParallaxClientOptions) -> None:
    route = respx.get(f"{BASE_URL}/records/{HASH}").mock(return_value=_record_response("published"))
    client = ParallaxClient(options)

    record = client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.001, poll_timeout=1.0))

    assert record.outcome.value == "published"
    assert route.call_count == 1


@respx.mock
def test_wait_for_record_retries_no_record_answered_then_published(options: ParallaxClientOptions) -> None:
    route = respx.get(f"{BASE_URL}/records/{HASH}").mock(
        side_effect=[
            _record_response("noRecordAnswered"),
            _record_response("noRecordAnswered"),
            _record_response("published"),
        ]
    )
    client = ParallaxClient(options)

    record = client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.001, poll_timeout=1.0))

    assert record.outcome.value == "published"
    assert route.call_count == 3


@respx.mock
def test_wait_for_record_returns_immediately_on_taken_down(options: ParallaxClientOptions) -> None:
    route = respx.get(f"{BASE_URL}/records/{HASH}").mock(return_value=_record_response("takenDown"))
    client = ParallaxClient(options)

    record = client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.001, poll_timeout=1.0))

    assert record.outcome.value == "takenDown"
    assert route.call_count == 1


@respx.mock
def test_wait_for_record_times_out_naming_the_hash(options: ParallaxClientOptions) -> None:
    respx.get(f"{BASE_URL}/records/{HASH}").mock(return_value=_record_response("retry"))
    client = ParallaxClient(options)

    with pytest.raises(ParallaxClientError) as excinfo:
        client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.005, poll_timeout=0.02))

    assert HASH in str(excinfo.value)
    assert "timed out" in str(excinfo.value)
    assert "retry" in str(excinfo.value)


@respx.mock
@pytest.mark.asyncio
async def test_async_wait_for_record_returns_on_first_published(options: ParallaxClientOptions) -> None:
    route = respx.get(f"{BASE_URL}/records/{HASH}").mock(return_value=_record_response("published"))
    client = AsyncParallaxClient(options)

    record = await client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.001, poll_timeout=1.0))

    assert record.outcome.value == "published"
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_async_wait_for_record_retries_no_record_answered_then_published(
    options: ParallaxClientOptions,
) -> None:
    route = respx.get(f"{BASE_URL}/records/{HASH}").mock(
        side_effect=[
            _record_response("noRecordAnswered"),
            _record_response("noRecordAnswered"),
            _record_response("published"),
        ]
    )
    client = AsyncParallaxClient(options)

    record = await client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.001, poll_timeout=1.0))

    assert record.outcome.value == "published"
    assert route.call_count == 3


@respx.mock
@pytest.mark.asyncio
async def test_async_wait_for_record_returns_immediately_on_taken_down(options: ParallaxClientOptions) -> None:
    route = respx.get(f"{BASE_URL}/records/{HASH}").mock(return_value=_record_response("takenDown"))
    client = AsyncParallaxClient(options)

    record = await client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.001, poll_timeout=1.0))

    assert record.outcome.value == "takenDown"
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_async_wait_for_record_times_out_naming_the_hash(options: ParallaxClientOptions) -> None:
    respx.get(f"{BASE_URL}/records/{HASH}").mock(return_value=_record_response("retry"))
    client = AsyncParallaxClient(options)

    with pytest.raises(ParallaxClientError) as excinfo:
        await client.wait_for_record(HASH, RecordWaitOptions(poll_interval=0.005, poll_timeout=0.02))

    assert HASH in str(excinfo.value)
    assert "timed out" in str(excinfo.value)
    assert "retry" in str(excinfo.value)
