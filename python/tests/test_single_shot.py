"""The single-shot calls on `ParallaxClient`: records, unregister, account stats, health, and refusals."""

from __future__ import annotations

import httpx
import pytest
import respx
from xio_parallax_client import ParallaxClient, ParallaxClientOptions, ParallaxProblem

from .conftest import BASE_URL


@respx.mock
def test_get_record_returns_the_parsed_model(options: ParallaxClientOptions) -> None:
    respx.get(f"{BASE_URL}/records/abc123").mock(
        return_value=httpx.Response(
            200,
            json={
                "originalImageHash": "abc123",
                "outcome": "published",
                "manifests": None,
                "verification": None,
                "failureReason": None,
            },
        )
    )
    client = ParallaxClient(options)
    record = client.get_record("abc123")
    assert record.original_image_hash == "abc123"
    assert record.outcome.value == "published"


@respx.mock
def test_get_record_raises_parallax_problem_on_404(options: ParallaxClientOptions) -> None:
    respx.get(f"{BASE_URL}/records/missing-hash").mock(
        return_value=httpx.Response(
            404,
            json={
                "type": "urn:xio:parallax:problem:record-not-found",
                "title": "Record not found",
                "status": 404,
            },
        )
    )
    client = ParallaxClient(options)
    with pytest.raises(ParallaxProblem) as excinfo:
        client.get_record("missing-hash")
    assert excinfo.value.status == 404
    assert excinfo.value.slug == "record-not-found"


@respx.mock
def test_unregister_succeeds_on_204(options: ParallaxClientOptions) -> None:
    route = respx.delete(f"{BASE_URL}/registrations/22222222-2222-2222-2222-222222222222").mock(
        return_value=httpx.Response(204)
    )
    client = ParallaxClient(options)
    assert client.unregister("22222222-2222-2222-2222-222222222222") is None
    assert route.called


@respx.mock
def test_account_stats_and_health(options: ParallaxClientOptions) -> None:
    respx.get(f"{BASE_URL}/account/stats").mock(
        return_value=httpx.Response(
            200,
            json={
                "registrations": {"grant": 100, "consumed": 1, "held": 0, "remaining": 99},
                "lookups": {"grant": 100, "consumed": 2, "held": 0, "remaining": 98},
                "callCount": 3,
            },
        )
    )
    respx.get(f"{BASE_URL}/health").mock(return_value=httpx.Response(200, json={"service": "parallax", "version": "1.0.0"}))

    client = ParallaxClient(options)
    stats = client.account_stats()
    assert int(stats.call_count) == 3
    health = client.health()
    assert health.service == "parallax"


@respx.mock
def test_admin_key_header_is_sent_when_configured() -> None:
    route = respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(200, json={"service": "parallax", "version": "1.0.0"})
    )
    options = ParallaxClientOptions(account_token="tok", admin_key="secret-admin-key", base_url=BASE_URL)
    client = ParallaxClient(options)
    client.health()
    assert route.calls.last.request.headers["X-Admin-Key"] == "secret-admin-key"
