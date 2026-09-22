"""`AsyncParallaxClient` is a thin mirror of `ParallaxClient`: same conversations, awaited."""

from __future__ import annotations

import httpx
import pytest
import respx
from xio_parallax_client import (
    AsyncParallaxClient,
    ImageUpload,
    ManifestForm,
    ManifestPart,
    ParallaxClientOptions,
    RegisterBatchOptions,
    RegistrationItem,
)
from xio_parallax_client.hashing import sha256_hex
from xio_parallax_client.problems import ParallaxClientError

from .conftest import BASE_URL

IMAGE = ImageUpload(file_name="async.png", content_type="image/png", data=b"async-image-bytes")
IMAGE_HASH = sha256_hex(IMAGE.data)


@respx.mock
@pytest.mark.asyncio
async def test_async_register_single_shot_sends_manifest_before_image(options: ParallaxClientOptions) -> None:
    route = respx.post(f"{BASE_URL}/registrations").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "11111111-1111-1111-1111-111111111111",
                "imageHash": IMAGE_HASH,
                "originalImageHash": None,
                "engineRecord": "opaque",
            },
        )
    )
    client = AsyncParallaxClient(options)
    manifest = ManifestPart(kind="xi-manifest", form=ManifestForm.JSON, data=b'{"k":"v"}')

    response = await client.register(IMAGE, [manifest])

    assert response.image_hash == IMAGE_HASH
    body = route.calls.last.request.content
    assert body.index(b'name="manifest[xi-manifest]"') < body.index(b'name="image"')


@respx.mock
@pytest.mark.asyncio
async def test_async_register_batch_happy_path(options: ParallaxClientOptions) -> None:
    respx.post(f"{BASE_URL}/slots").mock(
        return_value=httpx.Response(201, json={"slotId": "slot-async", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    respx.post(f"{BASE_URL}/slots/slot-async/uploads/missing").mock(
        return_value=httpx.Response(200, json={"missing": [IMAGE_HASH]})
    )
    respx.post(f"{BASE_URL}/slots/slot-async/uploads").mock(
        return_value=httpx.Response(
            200,
            json={
                "outcomes": [
                    {
                        "partIndex": 0,
                        "fileName": "async.png",
                        "accepted": True,
                        "imageHash": IMAGE_HASH,
                        "rejectionReason": None,
                        "registrationRemaining": 9,
                        "lookupRemaining": 9,
                        "registrationId": "33333333-3333-3333-3333-333333333333",
                    }
                ]
            },
        )
    )
    respx.post(f"{BASE_URL}/slots/slot-async/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "slot-async",
                "status": "committed",
                "entries": [
                    {
                        "imageHash": IMAGE_HASH,
                        "state": "retry",
                        "registrationId": "33333333-3333-3333-3333-333333333333",
                        "failureReason": None,
                    }
                ],
            },
        )
    )
    respx.get(f"{BASE_URL}/slots/slot-async/progress").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "slotId": "slot-async",
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
                        {
                            "imageHash": IMAGE_HASH,
                            "state": "retry",
                            "registrationId": "33333333-3333-3333-3333-333333333333",
                            "failureReason": None,
                        }
                    ],
                },
            ),
            httpx.Response(
                200,
                json={
                    "slotId": "slot-async",
                    "status": "committed",
                    "counts": {
                        "total": 1,
                        "held": 0,
                        "registered": 1,
                        "answered": 0,
                        "failed": 0,
                        "errata": 0,
                        "retry": 0,
                    },
                    "entries": [
                        {
                            "imageHash": IMAGE_HASH,
                            "state": "registered",
                            "registrationId": "33333333-3333-3333-3333-333333333333",
                            "failureReason": None,
                        }
                    ],
                },
            ),
        ]
    )

    client = AsyncParallaxClient(options)
    items = [RegistrationItem(image=IMAGE, manifests=[])]
    result = await client.register_batch(items, RegisterBatchOptions(poll_interval=0.001, poll_timeout=1.0))

    assert result.slot_id == "slot-async"
    assert result.final_progress.entries[0].state == "registered"
    assert len(result.upload_outcomes) == 1


@respx.mock
@pytest.mark.asyncio
async def test_async_register_batch_refuses_without_batching(unbatched_options: ParallaxClientOptions) -> None:
    client = AsyncParallaxClient(unbatched_options)
    items = [RegistrationItem(image=IMAGE, manifests=[])]
    with pytest.raises(ParallaxClientError, match="batching"):
        await client.register_batch(items, RegisterBatchOptions(poll_interval=0.01, poll_timeout=1.0))


@respx.mock
@pytest.mark.asyncio
async def test_async_register_batch_poll_timeout(options: ParallaxClientOptions) -> None:
    respx.post(f"{BASE_URL}/slots").mock(
        return_value=httpx.Response(201, json={"slotId": "slot-async-2", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    respx.post(f"{BASE_URL}/slots/slot-async-2/uploads/missing").mock(
        return_value=httpx.Response(200, json={"missing": [IMAGE_HASH]})
    )
    respx.post(f"{BASE_URL}/slots/slot-async-2/uploads").mock(
        return_value=httpx.Response(
            200,
            json={
                "outcomes": [
                    {
                        "partIndex": 0,
                        "fileName": "async.png",
                        "accepted": True,
                        "imageHash": IMAGE_HASH,
                        "rejectionReason": None,
                        "registrationRemaining": 9,
                        "lookupRemaining": 9,
                        "registrationId": None,
                    }
                ]
            },
        )
    )
    respx.post(f"{BASE_URL}/slots/slot-async-2/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "slot-async-2",
                "status": "committed",
                "entries": [{"imageHash": IMAGE_HASH, "state": "retry", "registrationId": None, "failureReason": None}],
            },
        )
    )
    respx.get(f"{BASE_URL}/slots/slot-async-2/progress").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "slot-async-2",
                "status": "committed",
                "counts": {"total": 1, "held": 0, "registered": 0, "answered": 0, "failed": 0, "errata": 0, "retry": 1},
                "entries": [{"imageHash": IMAGE_HASH, "state": "retry", "registrationId": None, "failureReason": None}],
            },
        )
    )

    client = AsyncParallaxClient(options)
    items = [RegistrationItem(image=IMAGE, manifests=[])]
    with pytest.raises(ParallaxClientError, match="timed out"):
        await client.register_batch(items, RegisterBatchOptions(poll_interval=0.005, poll_timeout=0.02))
