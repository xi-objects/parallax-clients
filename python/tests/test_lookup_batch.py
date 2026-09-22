"""`lookup_batch`: the `/lookup/slots` mirror of `register_batch` (images only, no manifests)."""

from __future__ import annotations

import httpx
import respx
from xio_parallax_client import ImageUpload, LookupBatchOptions, ParallaxClient, ParallaxClientOptions
from xio_parallax_client.hashing import sha256_hex

from .conftest import BASE_URL

QUERY_IMAGE = ImageUpload(file_name="query.jpg", content_type="image/jpeg", data=b"query-image-bytes")
QUERY_HASH = sha256_hex(QUERY_IMAGE.data)


@respx.mock
def test_lookup_batch_happy_path(options: ParallaxClientOptions) -> None:
    respx.post(f"{BASE_URL}/lookup/slots").mock(
        return_value=httpx.Response(201, json={"lookupSlotId": "lookup-1", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-1/queries/missing").mock(
        return_value=httpx.Response(200, json={"missing": [QUERY_HASH]})
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-1/queries").mock(
        return_value=httpx.Response(
            200,
            json={
                "outcomes": [
                    {
                        "partIndex": 0,
                        "fileName": "query.jpg",
                        "accepted": True,
                        "imageHash": QUERY_HASH,
                        "rejectionReason": None,
                        "registrationRemaining": 9,
                        "lookupRemaining": 9,
                        "registrationId": None,
                    }
                ]
            },
        )
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-1/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "lookupSlotId": "lookup-1",
                "queries": [{"imageHash": QUERY_HASH, "state": "retry", "result": None, "failureReason": None}],
            },
        )
    )
    respx.get(f"{BASE_URL}/lookup/slots/lookup-1/progress").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "slotId": "lookup-1",
                    "status": "committed",
                    "counts": {
                        "total": 1,
                        "held": 0,
                        "registered": 0,
                        "answered": 0,
                        "failed": 0,
                        "errata": 0,
                        "retry": 1,
                    },
                    "entries": [
                        {"imageHash": QUERY_HASH, "state": "retry", "registrationId": None, "failureReason": None}
                    ],
                },
            ),
            httpx.Response(
                200,
                json={
                    "slotId": "lookup-1",
                    "status": "committed",
                    "counts": {
                        "total": 1,
                        "held": 0,
                        "registered": 0,
                        "answered": 1,
                        "failed": 0,
                        "errata": 0,
                        "retry": 0,
                    },
                    "entries": [
                        {"imageHash": QUERY_HASH, "state": "answered", "registrationId": None, "failureReason": None}
                    ],
                },
            ),
        ]
    )
    respx.get(f"{BASE_URL}/lookup/slots/lookup-1/results").mock(
        return_value=httpx.Response(
            200,
            json={
                "lookupSlotId": "lookup-1",
                "queries": [
                    {
                        "imageHash": QUERY_HASH,
                        "state": "answered",
                        "result": {
                            "matched": True,
                            "matchedOriginalImageHashes": ["orig-hash"],
                            "candidates": [{"registrationId": "22222222-2222-2222-2222-222222222222"}],
                        },
                        "failureReason": None,
                    }
                ],
            },
        )
    )

    client = ParallaxClient(options)
    result = client.lookup_batch([QUERY_IMAGE], LookupBatchOptions(poll_interval=0.001, poll_timeout=1.0))

    queries_request = next(c.request for c in respx.calls if c.request.url.path == "/lookup/slots/lookup-1/queries")
    body = queries_request.content
    assert b'filename="query.jpg"' in body
    assert b"manifest[" not in body

    assert result.lookup_slot_id == "lookup-1"
    assert result.results.queries[0].result.matched is True
    assert result.final_progress.entries[0].state == "answered"


@respx.mock
def test_lookup_batch_refuses_without_batching(unbatched_options: ParallaxClientOptions) -> None:
    from xio_parallax_client.problems import ParallaxClientError

    client = ParallaxClient(unbatched_options)
    try:
        client.lookup_batch([QUERY_IMAGE], LookupBatchOptions(poll_interval=0.01, poll_timeout=1.0))
    except ParallaxClientError as exc:
        assert "batching" in str(exc)
    else:
        raise AssertionError("expected ParallaxClientError")
