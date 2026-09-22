"""Kind validation and the wire shape of `manifest[<kind>]` parts: name, content type, and order."""

from __future__ import annotations

import httpx
import pytest
import respx
from xio_parallax_client import ImageUpload, ManifestForm, ManifestPart, ParallaxClient, ParallaxClientOptions

from .conftest import BASE_URL


def test_manifest_part_accepts_a_valid_kind() -> None:
    part = ManifestPart(kind="xi-manifest.v1_2", form=ManifestForm.JSON, data=b"{}")
    assert part.kind == "xi-manifest.v1_2"


@pytest.mark.parametrize(
    "kind",
    [
        "",
        "has a space",
        "has/slash",
        "a" * 65,
        "brackets[x]",
    ],
)
def test_manifest_part_rejects_an_invalid_kind(kind: str) -> None:
    with pytest.raises(ValueError, match="manifest kind"):
        ManifestPart(kind=kind, form=ManifestForm.JSON, data=b"{}")


def test_manifest_form_content_types() -> None:
    assert ManifestForm.JSON.content_type == "application/json"
    assert ManifestForm.JUMBF.content_type == "application/jumbf"
    assert ManifestForm.C2PA.content_type == "application/c2pa"


@respx.mock
def test_register_sends_manifest_parts_before_image_with_bracketed_names() -> None:
    route = respx.post(f"{BASE_URL}/registrations").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "11111111-1111-1111-1111-111111111111",
                "imageHash": "abc123",
                "originalImageHash": None,
                "engineRecord": "opaque",
            },
        )
    )
    client = ParallaxClient(ParallaxClientOptions(account_token="tok", base_url=BASE_URL))
    image = ImageUpload(file_name="photo.png", content_type="image/png", data=b"raw-image-bytes")
    manifest = ManifestPart(kind="c2pa", form=ManifestForm.C2PA, data=b"jumbf-bytes")

    client.register(image, [manifest])

    request = route.calls.last.request
    body = request.content

    assert b'name="manifest[c2pa]"' in body
    assert b"Content-Type: application/c2pa" in body
    assert b'name="image"; filename="photo.png"' in body
    assert b"Content-Type: image/png" in body
    assert b"raw-image-bytes" in body
    # the manifest part precedes the image part
    assert body.index(b'name="manifest[c2pa]"') < body.index(b'name="image"')


@respx.mock
def test_lookup_sends_image_parts_with_no_manifest() -> None:
    route = respx.post(f"{BASE_URL}/lookup").mock(
        return_value=httpx.Response(200, json={"matched": False, "matchedOriginalImageHashes": [], "candidates": []})
    )
    client = ParallaxClient(ParallaxClientOptions(account_token="tok", base_url=BASE_URL))
    image = ImageUpload(file_name="query.jpg", content_type="image/jpeg", data=b"query-bytes")

    client.lookup(image)

    body = route.calls.last.request.content
    assert b'name="image"; filename="query.jpg"' in body
    assert b"Content-Type: image/jpeg" in body
    assert b"manifest[" not in body
