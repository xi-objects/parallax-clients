"""`lookup_batch`: the `/lookup/slots` mirror of `register_batch` (images only, no manifests).

A look-up commit is terminal and answers the results directly (see `look-up-in-batches.md`), so
`lookup_batch` never polls for them: it reads `progress` once, after commit, purely to report it,
and reads `results` only when the commit response body comes back empty.
"""

from __future__ import annotations

import json

import httpx
import respx
from xio_parallax_client import ImageUpload, LookupBatchOptions, ParallaxClient, ParallaxClientOptions
from xio_parallax_client.hashing import sha256_hex

from .conftest import BASE_URL

QUERY_IMAGE = ImageUpload(file_name="query.jpg", content_type="image/jpeg", data=b"query-image-bytes")
QUERY_HASH = sha256_hex(QUERY_IMAGE.data)


@respx.mock
def test_lookup_batch_commit_answers_a_retry_query_without_polling(options: ParallaxClientOptions) -> None:
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
    progress_route = respx.get(f"{BASE_URL}/lookup/slots/lookup-1/progress").mock(
        return_value=httpx.Response(
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
        )
    )
    # /results is deliberately not mocked: a look-up commit is terminal and answers the results
    # directly, so this call must never reach it.

    client = ParallaxClient(options)
    result = client.lookup_batch([QUERY_IMAGE], LookupBatchOptions())

    queries_request = next(c.request for c in respx.calls if c.request.url.path == "/lookup/slots/lookup-1/queries")
    body = queries_request.content
    assert b'filename="query.jpg"' in body
    assert b"manifest[" not in body

    assert result.lookup_slot_id == "lookup-1"
    assert result.results.queries[0].image_hash == QUERY_HASH
    assert result.results.queries[0].state == "retry"
    assert progress_route.call_count == 1
    assert not any(c.request.url.path == "/lookup/slots/lookup-1/results" for c in respx.calls)


@respx.mock
def test_lookup_batch_reads_results_once_when_commit_body_is_empty(options: ParallaxClientOptions) -> None:
    respx.post(f"{BASE_URL}/lookup/slots").mock(
        return_value=httpx.Response(201, json={"lookupSlotId": "lookup-2", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-2/queries/missing").mock(
        return_value=httpx.Response(200, json={"missing": [QUERY_HASH]})
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-2/queries").mock(
        return_value=httpx.Response(200, json={"outcomes": []})
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-2/commit").mock(return_value=httpx.Response(200, content=b""))
    respx.get(f"{BASE_URL}/lookup/slots/lookup-2/progress").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "lookup-2",
                "status": "committed",
                "counts": {"total": 1, "held": 0, "registered": 0, "answered": 1, "failed": 0, "errata": 0, "retry": 0},
                "entries": [
                    {"imageHash": QUERY_HASH, "state": "answered", "registrationId": None, "failureReason": None}
                ],
            },
        )
    )
    results_route = respx.get(f"{BASE_URL}/lookup/slots/lookup-2/results").mock(
        return_value=httpx.Response(
            200,
            json={
                "lookupSlotId": "lookup-2",
                "queries": [
                    {"imageHash": QUERY_HASH, "state": "answered", "result": {"matched": True}, "failureReason": None}
                ],
            },
        )
    )

    client = ParallaxClient(options)
    result = client.lookup_batch([QUERY_IMAGE], LookupBatchOptions())

    assert results_route.call_count == 1
    assert result.results.queries[0].state == "answered"


@respx.mock
def test_lookup_batch_with_duplicate_images_declares_and_uploads_the_hash_once(
    options: ParallaxClientOptions,
) -> None:
    duplicate = ImageUpload(file_name="query-again.jpg", content_type="image/jpeg", data=QUERY_IMAGE.data)

    respx.post(f"{BASE_URL}/lookup/slots").mock(
        return_value=httpx.Response(201, json={"lookupSlotId": "lookup-3", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    missing_route = respx.post(f"{BASE_URL}/lookup/slots/lookup-3/queries/missing").mock(
        return_value=httpx.Response(200, json={"missing": [QUERY_HASH]})
    )
    queries_route = respx.post(f"{BASE_URL}/lookup/slots/lookup-3/queries").mock(
        return_value=httpx.Response(200, json={"outcomes": []})
    )
    respx.post(f"{BASE_URL}/lookup/slots/lookup-3/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "lookupSlotId": "lookup-3",
                "queries": [{"imageHash": QUERY_HASH, "state": "answered", "result": None, "failureReason": None}],
            },
        )
    )
    respx.get(f"{BASE_URL}/lookup/slots/lookup-3/progress").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "lookup-3",
                "status": "committed",
                "counts": {"total": 1, "held": 0, "registered": 0, "answered": 1, "failed": 0, "errata": 0, "retry": 0},
                "entries": [
                    {"imageHash": QUERY_HASH, "state": "answered", "registrationId": None, "failureReason": None}
                ],
            },
        )
    )

    client = ParallaxClient(options)
    result = client.lookup_batch([QUERY_IMAGE, duplicate], LookupBatchOptions())

    declared = json.loads(missing_route.calls[0].request.content)
    assert declared["hashes"] == [QUERY_HASH]
    assert queries_route.call_count == 1
    assert len(result.results.queries) == 1
    assert result.results.queries[0].image_hash == QUERY_HASH


@respx.mock
def test_lookup_batch_refuses_without_batching(unbatched_options: ParallaxClientOptions) -> None:
    from xio_parallax_client.problems import ParallaxClientError

    client = ParallaxClient(unbatched_options)
    try:
        client.lookup_batch([QUERY_IMAGE], LookupBatchOptions())
    except ParallaxClientError as exc:
        assert "batching" in str(exc)
    else:
        raise AssertionError("expected ParallaxClientError")
