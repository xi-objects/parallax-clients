"""`register_batch`: open, resume via missing-hash declaration, upload, commit, poll to terminal."""

from __future__ import annotations

import httpx
import respx
from xio_parallax_client import (
    ImageUpload,
    ManifestForm,
    ManifestPart,
    ParallaxClient,
    ParallaxClientOptions,
    RegisterBatchOptions,
    RegistrationItem,
)
from xio_parallax_client.hashing import sha256_hex
from xio_parallax_client.problems import ParallaxClientError

from .conftest import BASE_URL

IMAGE_ONE = ImageUpload(file_name="one.png", content_type="image/png", data=b"image-one-bytes")
IMAGE_TWO = ImageUpload(file_name="two.png", content_type="image/png", data=b"image-two-bytes")
HASH_ONE = sha256_hex(IMAGE_ONE.data)
HASH_TWO = sha256_hex(IMAGE_TWO.data)


def _mock_conversation(missing: list[str], progress_states: list[list[str]]) -> None:
    respx.post(f"{BASE_URL}/slots").mock(
        return_value=httpx.Response(201, json={"slotId": "slot-1", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    respx.post(f"{BASE_URL}/slots/slot-1/uploads/missing").mock(
        return_value=httpx.Response(200, json={"missing": missing})
    )
    respx.post(f"{BASE_URL}/slots/slot-1/uploads").mock(
        return_value=httpx.Response(
            200,
            json={
                "outcomes": [
                    {
                        "partIndex": 0,
                        "fileName": "two.png",
                        "accepted": True,
                        "imageHash": HASH_TWO,
                        "rejectionReason": None,
                        "registrationRemaining": 9,
                        "lookupRemaining": 9,
                        "registrationId": "22222222-2222-2222-2222-222222222222",
                    }
                ]
            },
        )
    )
    respx.post(f"{BASE_URL}/slots/slot-1/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "slot-1",
                "status": "committed",
                "entries": [
                    {"imageHash": HASH_ONE, "state": "errata", "registrationId": None, "failureReason": None},
                    {
                        "imageHash": HASH_TWO,
                        "state": "retry",
                        "registrationId": "22222222-2222-2222-2222-222222222222",
                        "failureReason": None,
                    },
                ],
            },
        )
    )

    def _progress_payload(states: list[str]) -> dict:
        return {
            "slotId": "slot-1",
            "status": "committed",
            "counts": {"total": 2, "held": 0, "registered": 0, "answered": 0, "failed": 0, "errata": 1, "retry": 0},
            "entries": [
                {"imageHash": HASH_ONE, "state": "errata", "registrationId": None, "failureReason": None},
                {
                    "imageHash": HASH_TWO,
                    "state": states[0],
                    "registrationId": "22222222-2222-2222-2222-222222222222",
                    "failureReason": None,
                },
            ],
        }

    respx.get(f"{BASE_URL}/slots/slot-1/progress").mock(
        side_effect=[httpx.Response(200, json=_progress_payload(s)) for s in progress_states]
    )


@respx.mock
def test_register_batch_uploads_only_the_missing_hash(options: ParallaxClientOptions) -> None:
    _mock_conversation(missing=[HASH_TWO], progress_states=[["retry"], ["registered"]])
    client = ParallaxClient(options)
    manifest = ManifestPart(kind="c2pa", form=ManifestForm.C2PA, data=b"jumbf")
    items = [
        RegistrationItem(image=IMAGE_ONE, manifests=[manifest]),
        RegistrationItem(image=IMAGE_TWO, manifests=[]),
    ]
    seen_progress = []

    result = client.register_batch(
        items,
        RegisterBatchOptions(poll_interval=0.001, poll_timeout=1.0),
        on_progress=seen_progress.append,
    )

    upload_request = next(c.request for c in respx.calls if c.request.url.path == "/slots/slot-1/uploads")
    body = upload_request.content
    assert b'filename="two.png"' in body
    assert b'filename="one.png"' not in body
    assert b'name="manifest[c2pa]"' not in body  # image two carries no manifest

    assert result.slot_id == "slot-1"
    assert result.commit.status == "committed"
    assert len(result.upload_outcomes) == 1
    assert result.upload_outcomes[0].image_hash == HASH_TWO
    assert result.final_progress.entries[1].state == "registered"
    # the errata entry (already registered) is returned as-is, never raised for
    assert result.final_progress.entries[0].state == "errata"
    assert len(seen_progress) == 2


@respx.mock
def test_register_batch_refuses_without_batching(unbatched_options: ParallaxClientOptions) -> None:
    client = ParallaxClient(unbatched_options)
    items = [RegistrationItem(image=IMAGE_ONE, manifests=[])]
    try:
        client.register_batch(items, RegisterBatchOptions(poll_interval=0.01, poll_timeout=1.0))
    except ParallaxClientError as exc:
        assert "batching" in str(exc)
    else:
        raise AssertionError("expected ParallaxClientError")


@respx.mock
def test_register_batch_poll_timeout(options: ParallaxClientOptions) -> None:
    respx.post(f"{BASE_URL}/slots").mock(
        return_value=httpx.Response(201, json={"slotId": "slot-2", "expiresAt": "2026-01-01T00:00:00Z"})
    )
    respx.post(f"{BASE_URL}/slots/slot-2/uploads/missing").mock(
        return_value=httpx.Response(200, json={"missing": [HASH_ONE]})
    )
    respx.post(f"{BASE_URL}/slots/slot-2/uploads").mock(
        return_value=httpx.Response(
            200,
            json={
                "outcomes": [
                    {
                        "partIndex": 0,
                        "fileName": "one.png",
                        "accepted": True,
                        "imageHash": HASH_ONE,
                        "rejectionReason": None,
                        "registrationRemaining": 9,
                        "lookupRemaining": 9,
                        "registrationId": "22222222-2222-2222-2222-222222222222",
                    }
                ]
            },
        )
    )
    respx.post(f"{BASE_URL}/slots/slot-2/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "slot-2",
                "status": "committed",
                "entries": [
                    {
                        "imageHash": HASH_ONE,
                        "state": "retry",
                        "registrationId": None,
                        "failureReason": None,
                    }
                ],
            },
        )
    )
    respx.get(f"{BASE_URL}/slots/slot-2/progress").mock(
        return_value=httpx.Response(
            200,
            json={
                "slotId": "slot-2",
                "status": "committed",
                "counts": {"total": 1, "held": 0, "registered": 0, "answered": 0, "failed": 0, "errata": 0, "retry": 1},
                "entries": [{"imageHash": HASH_ONE, "state": "retry", "registrationId": None, "failureReason": None}],
            },
        )
    )

    client = ParallaxClient(options)
    items = [RegistrationItem(image=IMAGE_ONE, manifests=[])]
    try:
        client.register_batch(items, RegisterBatchOptions(poll_interval=0.005, poll_timeout=0.02))
    except ParallaxClientError as exc:
        assert "timed out" in str(exc)
    else:
        raise AssertionError("expected ParallaxClientError on poll timeout")
