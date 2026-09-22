"""Detection of an embedded C2PA manifest store across the supported carriers, and the refusals."""

from __future__ import annotations

from xio_parallax_client import C2paCarrier, ManifestForm, as_manifest_part, detect_embedded_c2pa

from .carriers import CBOR_UUID, box, jpeg, png, superbox, synthetic_store, tiff, webp


def test_jpeg_reassembles_three_app11_segments_out_of_order() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(jpeg(store, pieces=3, order=[3, 1, 2]))
    assert result.carrier is C2paCarrier.JPEG
    assert result.store is not None
    assert result.store.data == store
    assert result.store.boxes[0].label == "c2pa"


def test_jpeg_without_app11_has_no_store() -> None:
    result = detect_embedded_c2pa(jpeg(None))
    assert result.carrier is C2paCarrier.JPEG
    assert result.store is None
    assert "no C2PA" in result.detail


def test_jpeg_ignores_a_jumbf_box_that_is_not_c2pa() -> None:
    other = superbox(CBOR_UUID, "not-c2pa", box(b"cbor", bytes(1)))
    assert detect_embedded_c2pa(jpeg(other)).store is None


def test_jpeg_repeated_sequence_number_is_malformed() -> None:
    result = detect_embedded_c2pa(jpeg(synthetic_store(), pieces=3, order=[1, 1, 2]))
    assert result.store is None
    assert result.detail.startswith("malformed JPEG")


def test_png_cabx_chunk_is_the_store() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(png(store))
    assert result.carrier is C2paCarrier.PNG
    assert result.store is not None
    assert result.store.data == store


def test_png_with_a_bad_crc_is_malformed() -> None:
    data = bytearray(png(synthetic_store()))
    data[-20] ^= 0xFF
    result = detect_embedded_c2pa(bytes(data))
    assert result.store is None
    assert "CRC" in result.detail


def test_png_cabx_that_is_not_a_jumb_box_is_malformed() -> None:
    result = detect_embedded_c2pa(png(b"not a jumbf box at all"))
    assert result.store is None
    assert result.detail.startswith("malformed PNG:")


def test_png_cabx_jumb_box_that_is_not_a_c2pa_store_is_malformed() -> None:
    other = superbox(CBOR_UUID, "not-c2pa", box(b"cbor", bytes(1)))
    result = detect_embedded_c2pa(png(other))
    assert result.store is None
    assert result.detail.startswith("malformed PNG:")


def test_png_without_cabx_chunk_has_no_store() -> None:
    result = detect_embedded_c2pa(png(None))
    assert result.carrier is C2paCarrier.PNG
    assert result.store is None
    assert "no C2PA manifest store" in result.detail


def test_webp_c2pa_chunk_is_the_store() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(webp(store))
    assert result.carrier is C2paCarrier.WEBP
    assert result.store is not None
    assert result.store.data == store


def test_webp_without_c2pa_chunk_has_no_store() -> None:
    result = detect_embedded_c2pa(webp(None))
    assert result.carrier is C2paCarrier.WEBP
    assert result.store is None
    assert "no C2PA manifest store" in result.detail


def test_webp_c2pa_chunk_that_is_not_a_jumb_box_is_malformed() -> None:
    result = detect_embedded_c2pa(webp(b"not a jumbf box at all"))
    assert result.store is None
    assert result.detail.startswith("malformed WEBP:")


def test_tiff_tag_0xcd41_is_the_store() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(tiff(store))
    assert result.carrier is C2paCarrier.TIFF
    assert result.store is not None
    assert result.store.data == store


def test_tiff_tag_that_is_not_a_jumb_box_is_malformed() -> None:
    result = detect_embedded_c2pa(tiff(b"not a jumbf box at all"))
    assert result.store is None
    assert result.detail.startswith("malformed TIFF:")


def test_gif_is_unsupported_never_no_c2pa() -> None:
    result = detect_embedded_c2pa(b"GIF89a" + bytes([1, 0, 1, 0, 0, 0, 0]) + b";")
    assert result.carrier is C2paCarrier.UNSUPPORTED
    assert result.store is None
    assert "not known" in result.detail


def test_truncated_png_is_malformed_not_absent() -> None:
    result = detect_embedded_c2pa(png(synthetic_store())[:40])
    assert result.carrier is C2paCarrier.PNG
    assert result.store is None
    assert result.detail.startswith("malformed PNG")


def test_box_walk_lists_every_box_with_labels_and_depths() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(png(store))
    assert result.store is not None
    shown = [(b.type, b.label, b.depth) for b in result.store.boxes]
    assert shown == [
        ("jumb", "c2pa", 0),
        ("jumd", "c2pa", 1),
        ("jumb", "urn:uuid:test-manifest", 1),
        ("jumd", "urn:uuid:test-manifest", 2),
        ("jumb", "c2pa.claim", 2),
        ("jumd", "c2pa.claim", 3),
        ("cbor", None, 3),
    ]
    assert result.store.boxes[0].length == len(store)
    assert result.detail.startswith("C2PA manifest store")


def test_as_manifest_part_is_kind_c2pa_form_c2pa_same_bytes() -> None:
    result = detect_embedded_c2pa(png(synthetic_store()))
    assert result.store is not None
    part = as_manifest_part(result.store)
    assert part.kind == "c2pa"
    assert part.form is ManifestForm.C2PA
    assert part.data == result.store.data
