"""Detection of embedded JUMBF manifest stores across the supported carriers, their classification, and refusals."""

from __future__ import annotations

from xio_parallax_client import (
    C2paCarrier,
    EmbeddedC2paOutcome,
    ManifestForm,
    as_manifest_part,
    detect_embedded_c2pa,
)

from .carriers import C2PA_UUID, box, jpeg, other_store, png, superbox, synthetic_store, tiff, webp


def test_jpeg_reassembles_three_app11_segments_out_of_order() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(jpeg(store, pieces=3, order=[3, 1, 2]))
    assert result.carrier is C2paCarrier.JPEG
    assert result.outcome is EmbeddedC2paOutcome.FOUND
    assert [s.data for s in result.stores] == [store]
    assert result.stores[0].boxes[0].label == "c2pa"


def test_jpeg_without_app11_is_absent() -> None:
    result = detect_embedded_c2pa(jpeg(None))
    assert result.carrier is C2paCarrier.JPEG
    assert result.outcome is EmbeddedC2paOutcome.ABSENT
    assert result.stores == []
    assert "no embedded JUMBF manifest store" in result.detail


def test_c2pa_uuid_and_label_classify_as_kind_c2pa() -> None:
    result = detect_embedded_c2pa(png(synthetic_store()))
    assert result.outcome is EmbeddedC2paOutcome.FOUND
    assert [s.kind for s in result.stores] == ["c2pa"]


def test_another_description_classifies_as_kind_jumbf_never_refused() -> None:
    result = detect_embedded_c2pa(png(other_store()))
    assert result.outcome is EmbeddedC2paOutcome.FOUND
    assert [s.kind for s in result.stores] == ["jumbf"]


def test_c2pa_uuid_without_the_c2pa_label_classifies_as_kind_jumbf() -> None:
    result = detect_embedded_c2pa(webp(superbox(C2PA_UUID, "not-c2pa")))
    assert [s.kind for s in result.stores] == ["jumbf"]


def test_jpeg_with_two_instances_of_different_kinds_yields_both_in_document_order() -> None:
    first, second = other_store(), synthetic_store()
    result = detect_embedded_c2pa(jpeg(first, extra=(second,), first_en=9))
    assert result.outcome is EmbeddedC2paOutcome.FOUND
    assert [(s.kind, s.data) for s in result.stores] == [("jumbf", first), ("c2pa", second)]


def test_jpeg_with_two_instances_of_one_kind_is_malformed_naming_the_count() -> None:
    result = detect_embedded_c2pa(jpeg(synthetic_store(), extra=(synthetic_store(),)))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.stores == []
    assert result.detail.startswith("malformed JPEG:")
    assert "2 embedded manifest stores classify as kind 'c2pa'" in result.detail


def test_jpeg_with_one_malformed_instance_is_malformed_as_a_whole() -> None:
    result = detect_embedded_c2pa(jpeg(synthetic_store(), extra=(box(b"jumb", box(b"cbor", bytes(4))),)))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.stores == []


def test_jpeg_app11_instance_that_is_not_jumb_is_ignored() -> None:
    result = detect_embedded_c2pa(jpeg(synthetic_store(), extra=(box(b"LCHK", bytes(12)),)))
    assert result.outcome is EmbeddedC2paOutcome.FOUND
    assert [s.kind for s in result.stores] == ["c2pa"]


def test_jpeg_jp_segment_too_short_for_its_box_header_is_malformed() -> None:
    data = jpeg(None)
    short = bytes([0xFF, 0xEB, 0x00, 0x10]) + b"JP" + bytes(12)
    result = detect_embedded_c2pa(data[:20] + short + data[20:])
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert "APP11 JP segment of 14 bytes" in result.detail


def test_jumd_label_that_is_not_utf8_is_replaced_never_refused() -> None:
    store = box(b"jumb", box(b"jumd", C2PA_UUID + bytes([0x03, 0xFF, 0xFE, 0x00])))
    result = detect_embedded_c2pa(png(store))
    assert [(s.kind, s.boxes[0].label) for s in result.stores] == [("jumbf", chr(0xFFFD) * 2)]


def test_jpeg_repeated_sequence_number_is_malformed() -> None:
    result = detect_embedded_c2pa(jpeg(synthetic_store(), pieces=3, order=[1, 1, 2]))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.detail.startswith("malformed JPEG")


def test_png_with_a_bad_crc_is_malformed() -> None:
    data = bytearray(png(synthetic_store()))
    data[-20] ^= 0xFF
    result = detect_embedded_c2pa(bytes(data))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert "CRC" in result.detail


def test_png_cabx_that_is_not_a_jumb_box_is_malformed() -> None:
    result = detect_embedded_c2pa(png(b"not a jumbf box at all"))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.stores == []
    assert result.detail.startswith("malformed PNG:")


def test_png_without_cabx_chunk_is_absent() -> None:
    result = detect_embedded_c2pa(png(None))
    assert result.carrier is C2paCarrier.PNG
    assert result.outcome is EmbeddedC2paOutcome.ABSENT


def test_webp_c2pa_chunk_is_the_store() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(webp(store))
    assert result.carrier is C2paCarrier.WEBP
    assert [s.data for s in result.stores] == [store]


def test_webp_without_c2pa_chunk_is_absent() -> None:
    result = detect_embedded_c2pa(webp(None))
    assert result.carrier is C2paCarrier.WEBP
    assert result.outcome is EmbeddedC2paOutcome.ABSENT


def test_webp_c2pa_chunk_that_is_not_a_jumb_box_is_malformed() -> None:
    result = detect_embedded_c2pa(webp(b"not a jumbf box at all"))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.detail.startswith("malformed WEBP:")


def test_tiff_tag_0xcd41_is_the_store() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(tiff(store))
    assert result.carrier is C2paCarrier.TIFF
    assert [s.data for s in result.stores] == [store]


def test_tiff_tag_that_is_not_a_jumb_box_is_malformed() -> None:
    result = detect_embedded_c2pa(tiff(b"not a jumbf box at all"))
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.detail.startswith("malformed TIFF:")


def test_gif_is_unsupported_never_absent() -> None:
    result = detect_embedded_c2pa(b"GIF89a" + bytes([1, 0, 1, 0, 0, 0, 0]) + b";")
    assert result.carrier is C2paCarrier.UNSUPPORTED
    assert result.outcome is EmbeddedC2paOutcome.UNSUPPORTED
    assert result.stores == []
    assert "not known" in result.detail


def test_truncated_png_is_malformed_not_absent() -> None:
    result = detect_embedded_c2pa(png(synthetic_store())[:40])
    assert result.carrier is C2paCarrier.PNG
    assert result.outcome is EmbeddedC2paOutcome.MALFORMED
    assert result.detail.startswith("malformed PNG")


def test_box_walk_lists_every_box_with_labels_and_depths() -> None:
    store = synthetic_store()
    result = detect_embedded_c2pa(png(store))
    shown = [(b.type, b.label, b.depth) for b in result.stores[0].boxes]
    assert shown == [
        ("jumb", "c2pa", 0),
        ("jumd", "c2pa", 1),
        ("jumb", "urn:uuid:test-manifest", 1),
        ("jumd", "urn:uuid:test-manifest", 2),
        ("jumb", "c2pa.claim", 2),
        ("jumd", "c2pa.claim", 3),
        ("cbor", None, 3),
    ]
    assert result.stores[0].boxes[0].length == len(store)
    assert result.detail.startswith("c2pa manifest store")


def test_as_manifest_part_kind_and_form_follow_the_classification() -> None:
    first, second = other_store(), synthetic_store()
    stores = detect_embedded_c2pa(jpeg(first, extra=(second,))).stores
    parts = [as_manifest_part(store) for store in stores]
    assert [(p.kind, p.form, p.data) for p in parts] == [
        ("jumbf", ManifestForm.JUMBF, first),
        ("c2pa", ManifestForm.C2PA, second),
    ]
