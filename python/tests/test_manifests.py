"""Manifest selection and the conflict rule, resolved per image and over a whole collection."""

from __future__ import annotations

import pytest
from xio_parallax_client import (
    NO_MANIFESTS,
    ImageUpload,
    ManifestForm,
    ManifestRefusalError,
    ManifestRequest,
    ManifestSelection,
    SidecarManifest,
    resolve_image_manifests,
    resolve_manifests,
)

from .carriers import jpeg, other_store, png, synthetic_store

_EMBEDDED = ManifestSelection(include_embedded=True)
_GIF = b"GIF89a" + bytes([1, 0, 1, 0, 0, 0, 0]) + b";"


def _image(data: bytes, name: str = "a.png") -> ImageUpload:
    """An image upload of `data` under `name`."""
    return ImageUpload(file_name=name, content_type="image/png", data=data)


def _sidecars(*sidecars: SidecarManifest, include_embedded: bool = False) -> ManifestSelection:
    """A selection of the given sidecars."""
    return ManifestSelection(include_embedded=include_embedded, sidecars=sidecars)


def _refusal(image: ImageUpload, selection: ManifestSelection) -> str:
    """The one reason resolving `image` with `selection` refuses."""
    with pytest.raises(ManifestRefusalError) as refused:
        resolve_image_manifests(image, selection)
    [refusal] = refused.value.refusals
    assert refusal.file_name == image.file_name
    return refusal.reason


def test_no_manifests_yields_no_parts_even_on_an_unsupported_carrier() -> None:
    assert resolve_image_manifests(_image(_GIF), NO_MANIFESTS) == []


def test_embedded_found_is_included_with_its_classified_kind() -> None:
    [part] = resolve_image_manifests(_image(png(other_store())), _EMBEDDED)
    assert (part.kind, part.form, part.data) == ("jumbf", ManifestForm.JUMBF, other_store())


def test_embedded_absent_yields_nothing() -> None:
    assert resolve_image_manifests(_image(png(None)), _EMBEDDED) == []


def test_embedded_malformed_refuses() -> None:
    assert "malformed PNG" in _refusal(_image(png(b"not jumbf")), _EMBEDDED)


def test_unsupported_carrier_in_embedded_mode_refuses() -> None:
    assert "cannot be said" in _refusal(_image(_GIF), _EMBEDDED)


def test_json_sidecar_and_embedded_block_coexist() -> None:
    selection = _sidecars(SidecarManifest.json("a.json", "xi-manifest", b"{}"), include_embedded=True)
    parts = resolve_image_manifests(_image(png(synthetic_store())), selection)
    assert [(p.kind, p.form) for p in parts] == [("xi-manifest", ManifestForm.JSON), ("c2pa", ManifestForm.C2PA)]


def test_embedded_block_equal_to_a_json_sidecar_is_still_included() -> None:
    selection = _sidecars(SidecarManifest.json("a.json", "xi-manifest", synthetic_store()), include_embedded=True)
    parts = resolve_image_manifests(_image(png(synthetic_store())), selection)
    assert [p.kind for p in parts] == ["xi-manifest", "c2pa"]


def test_two_byte_identical_jumbf_sidecars_go_on_the_wire_once() -> None:
    twins = (SidecarManifest.jumbf("a.c2pa", synthetic_store()), SidecarManifest.jumbf("b.c2pa", synthetic_store()))
    selection = _sidecars(*twins)
    assert [p.kind for p in resolve_image_manifests(_image(png(None)), selection)] == ["c2pa"]


def test_malformed_embedded_block_refuses_in_sidecar_mode() -> None:
    selection = _sidecars(SidecarManifest.jumbf("a.c2pa", synthetic_store()))
    assert "malformed PNG" in _refusal(_image(png(b"not jumbf")), selection)


def test_byte_identical_jumbf_sidecar_is_included_once() -> None:
    selection = _sidecars(SidecarManifest.jumbf("a.c2pa", synthetic_store()), include_embedded=True)
    parts = resolve_image_manifests(_image(png(synthetic_store())), selection)
    assert [(p.kind, p.form, p.data) for p in parts] == [("c2pa", ManifestForm.C2PA, synthetic_store())]


def test_jumbf_sidecar_differing_from_the_embedded_block_refuses_even_in_sidecar_mode() -> None:
    selection = _sidecars(SidecarManifest.jumbf("a.jumbf", other_store("sidecar")))
    assert "'a.jumbf' matches no manifest store" in _refusal(_image(png(other_store())), selection)


def test_embedded_block_matching_no_jumbf_sidecar_refuses() -> None:
    image = _image(jpeg(other_store(), extra=(synthetic_store(),)), "a.jpg")
    selection = _sidecars(SidecarManifest.jumbf("a.c2pa", synthetic_store()))
    assert "embedded jumbf manifest store 1 of 2 matches no JUMBF sidecar" in _refusal(image, selection)


def test_jumbf_sidecar_beside_an_unsupported_carrier_refuses() -> None:
    selection = _sidecars(SidecarManifest.jumbf("a.c2pa", synthetic_store()))
    assert "cannot be said" in _refusal(_image(_GIF, "a.gif"), selection)


def test_jumbf_sidecar_beside_a_carrier_with_no_block_is_included_alone() -> None:
    selection = _sidecars(SidecarManifest.jumbf("a.jumbf", other_store()))
    [part] = resolve_image_manifests(_image(png(None)), selection)
    assert (part.kind, part.form) == ("jumbf", ManifestForm.JUMBF)


def test_malformed_jumbf_sidecar_refuses_naming_it() -> None:
    selection = _sidecars(SidecarManifest.jumbf("a.c2pa", b"not jumbf"))
    assert "JUMBF sidecar 'a.c2pa' is not well-formed" in _refusal(_image(png(None)), selection)


def test_two_manifests_of_one_kind_refuse() -> None:
    selection = _sidecars(SidecarManifest.json("a.json", "c2pa", b"{}"), include_embedded=True)
    assert "2 manifests are of kind 'c2pa'" in _refusal(_image(png(synthetic_store())), selection)


def test_wire_order_is_sidecars_then_embedded_blocks_in_document_order() -> None:
    image = _image(jpeg(other_store(), extra=(synthetic_store(),)), "a.jpg")
    selection = _sidecars(SidecarManifest.json("a.json", "xi-manifest", b"{}"), include_embedded=True)
    assert [p.kind for p in resolve_image_manifests(image, selection)] == ["xi-manifest", "jumbf", "c2pa"]


def test_a_collection_with_two_bad_items_lists_both_and_returns_nothing() -> None:
    requests = [
        ManifestRequest(_image(png(b"not jumbf"), "bad-1.png"), _EMBEDDED),
        ManifestRequest(_image(png(synthetic_store()), "good.png"), _EMBEDDED),
        ManifestRequest(_image(_GIF, "bad-2.gif"), _EMBEDDED),
    ]
    with pytest.raises(ManifestRefusalError) as refused:
        resolve_manifests(requests)
    assert [r.file_name for r in refused.value.refusals] == ["bad-1.png", "bad-2.gif"]
    lines = str(refused.value).splitlines()
    assert "2 image(s)" in lines[0]
    assert lines[1].startswith("bad-1.png: ") and lines[2].startswith("bad-2.gif: ")


def test_a_clean_collection_yields_one_item_per_request_in_order() -> None:
    requests = [
        ManifestRequest(_image(png(synthetic_store()), "one.png"), _EMBEDDED),
        ManifestRequest(_image(_GIF, "two.gif"), NO_MANIFESTS),
    ]
    shown = [(i.image.file_name, [m.kind for m in i.manifests]) for i in resolve_manifests(requests)]
    assert shown == [("one.png", ["c2pa"]), ("two.gif", [])]


def test_sidecar_validation_name_json_kind_jumbf_no_kind_c2pa_form_refused() -> None:
    with pytest.raises(ValueError, match="needs the manifest kind"):
        SidecarManifest("a.json", ManifestForm.JSON, None, b"{}")
    with pytest.raises(ValueError, match="must match"):
        SidecarManifest.json("a.json", "bad kind", b"{}")
    with pytest.raises(ValueError, match="takes no kind"):
        SidecarManifest("a.jumbf", ManifestForm.JUMBF, "c2pa", b"")
    with pytest.raises(ValueError, match="needs a name"):
        SidecarManifest.json(" ", "xi-manifest", b"{}")
    with pytest.raises(ValueError, match="never an input"):
        SidecarManifest("a.c2pa", ManifestForm.C2PA, None, b"")
