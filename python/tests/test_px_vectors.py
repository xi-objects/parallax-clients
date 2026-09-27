"""Conformance: every vendored PX Frame vector, decoded and re-encoded through the seam.

# PC-109: the conformance suite over `vectors/px-frame`, run through `PxFrameCodec` only

Runs entirely through `xio_parallax_client.frames`'s public seam (`PxFrameCodec`, resolved via
`frames.binding.default_frame_codec`); nothing here imports `frames.pure`, so a future binding
proves itself against these same vectors by adding one entry to `BINDINGS`. Vectors are discovered
from `python/tests/vectors/px-frame` by glob, never a hand-kept list; a missing vectors directory
fails the suite rather than skipping it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from xio_parallax_client.frames import (
    PxBodyHeader,
    PxBucketContent,
    PxChainBuilt,
    PxChainMember,
    PxEndHeader,
    PxFrameAccepted,
    PxFrameCodec,
    PxFrameHeader,
    PxFrameRefusal,
    PxFrameRefused,
    PxFrameType,
    PxGapHeader,
    PxGapRange,
    PxHeadHeader,
)
from xio_parallax_client.frames.binding import default_frame_codec

# PC-109: every binding this suite proves; a new one is one entry here
BINDINGS: list[PxFrameCodec] = [default_frame_codec()]

_VECTORS_DIR = Path(__file__).resolve().parent / "vectors" / "px-frame"
_FRAMES_DIR = _VECTORS_DIR / "frames"
_CHAINS_DIR = _VECTORS_DIR / "chains"


def _require_vectors_dir() -> None:
    """PC-109: a missing vectors directory is a test failure, not a skip."""
    if not _VECTORS_DIR.is_dir():
        pytest.fail(f"vectors directory is missing: {_VECTORS_DIR} (run scripts/vendor-px-vectors.sh)")


_require_vectors_dir()


def _sidecar(pxf_path: Path) -> dict[str, Any]:
    return json.loads(pxf_path.with_suffix(".json").read_text(encoding="utf-8"))


def _frame_vector_names() -> list[str]:
    _require_vectors_dir()
    return sorted(path.stem for path in _FRAMES_DIR.glob("*.pxf"))


def _accepted_vector_names() -> list[str]:
    return [name for name in _frame_vector_names() if _sidecar(_FRAMES_DIR / f"{name}.pxf")["expect"] == "accepted"]


def _refused_vector_names() -> list[str]:
    return [name for name in _frame_vector_names() if _sidecar(_FRAMES_DIR / f"{name}.pxf")["expect"] == "refused"]


def _chain_fixture_names() -> list[str]:
    _require_vectors_dir()
    return sorted(path.name for path in _CHAINS_DIR.iterdir() if path.is_dir())


def _binding_id(codec: PxFrameCodec) -> str:
    return type(codec).__name__


def _header_from_sidecar(sidecar: dict[str, Any], sequence_id: Any) -> PxFrameHeader:
    """PC-109: rebuild the header the sidecar's own fields describe, by frame type."""
    frame_type = PxFrameType[sidecar["type"]]
    frame_id = int(sidecar["frameId"])
    if frame_type is PxFrameType.HEAD:
        return PxHeadHeader(sequence_id=sequence_id, frame_id=frame_id)
    if frame_type is PxFrameType.BODY:
        return PxBodyHeader(
            sequence_id=sequence_id,
            frame_id=frame_id,
            prev=int(sidecar["prev"]),
            next=int(sidecar["next"]),
            source_time_offset_microseconds=int(sidecar["sourceTimeOffsetMicroseconds"]),
        )
    if frame_type is PxFrameType.END:
        return PxEndHeader(sequence_id=sequence_id, frame_id=frame_id, prev=int(sidecar["prev"]))
    return PxGapHeader(
        sequence_id=sequence_id,
        frame_id=frame_id,
        range=PxGapRange(range_from=int(sidecar["rangeFrom"]), range_to=int(sidecar["rangeTo"])),
    )


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
def test_every_pxf_has_a_sidecar_and_every_sidecar_a_pxf(codec: PxFrameCodec) -> None:
    """PC-109: the vendored frame directory pairs every `.pxf` with a `.json` sidecar, and vice versa."""
    del codec
    pxf_stems = {path.stem for path in _FRAMES_DIR.glob("*.pxf")}
    json_stems = {path.stem for path in _FRAMES_DIR.glob("*.json")}
    assert pxf_stems == json_stems
    assert pxf_stems, "no frame vectors found"


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
def test_every_frame_type_has_an_accepted_vector(codec: PxFrameCodec) -> None:
    """PC-109: each `PxFrameType` has at least one accepted vector exercising it."""
    del codec
    accepted_types = {_sidecar(_FRAMES_DIR / f"{name}.pxf")["type"] for name in _accepted_vector_names()}
    assert accepted_types == {member.name for member in PxFrameType}


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
def test_every_frame_refusal_has_a_refused_vector(codec: PxFrameCodec) -> None:
    """PC-109: each `PxFrameRefusal` has at least one refused vector naming it as the reason."""
    del codec
    refused_reasons = {_sidecar(_FRAMES_DIR / f"{name}.pxf")["reason"] for name in _refused_vector_names()}
    assert refused_reasons == {member.value for member in PxFrameRefusal}


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
@pytest.mark.parametrize("name", _accepted_vector_names())
def test_accepted_vector_decodes_to_its_sidecar_and_reencodes_byte_identical(name: str, codec: PxFrameCodec) -> None:
    """PC-109: decode compares every sidecar field, including bucket and frame hashes; re-encode is byte identical."""
    pxf_path = _FRAMES_DIR / f"{name}.pxf"
    sidecar = _sidecar(pxf_path)
    frame_bytes = pxf_path.read_bytes()

    result = codec.decode(frame_bytes)
    assert isinstance(result, PxFrameAccepted), f"{name}: expected accepted, got {result!r}"
    frame = result.frame

    assert frame.header.frame_type.name == sidecar["type"]
    assert str(frame.header.sequence_id) == sidecar["sequenceId"]
    assert frame.header.frame_id == int(sidecar["frameId"])

    if isinstance(frame.header, PxBodyHeader):
        assert frame.header.prev == int(sidecar["prev"])
        assert frame.header.next == int(sidecar["next"])
        assert frame.header.source_time_offset_microseconds == int(sidecar["sourceTimeOffsetMicroseconds"])
    elif isinstance(frame.header, PxEndHeader):
        assert frame.header.prev == int(sidecar["prev"])
    elif isinstance(frame.header, PxGapHeader):
        assert frame.header.range.range_from == int(sidecar["rangeFrom"])
        assert frame.header.range.range_to == int(sidecar["rangeTo"])

    sidecar_buckets = sidecar.get("buckets", [])
    assert len(frame.buckets) == len(sidecar_buckets)
    for bucket, expected in zip(frame.buckets, sidecar_buckets, strict=True):
        assert bucket.entry.tag == expected["tag"]
        assert bucket.entry.length == expected["length"]
        assert bucket.entry.hash.hex() == expected["hash"]

    assert frame.frame_hash.hex() == sidecar["frameHash"]

    header = _header_from_sidecar(sidecar, frame.header.sequence_id)
    buckets = tuple(PxBucketContent(tag=bucket.entry.tag, data=bucket.data) for bucket in frame.buckets)
    encoded = codec.encode(header, buckets)
    assert encoded.frame == frame_bytes, f"{name}: re-encode is not byte identical"
    assert encoded.frame_hash.hex() == sidecar["frameHash"]


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
@pytest.mark.parametrize("name", _refused_vector_names())
def test_refused_vector_answers_its_sidecar_reason(name: str, codec: PxFrameCodec) -> None:
    """PC-109: a refused vector decodes to exactly the reason its sidecar names."""
    pxf_path = _FRAMES_DIR / f"{name}.pxf"
    sidecar = _sidecar(pxf_path)
    result = codec.decode(pxf_path.read_bytes())
    assert isinstance(result, PxFrameRefused), f"{name}: expected refused, got {result!r}"
    assert result.reason is PxFrameRefusal(sidecar["reason"])


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
def test_both_chain_fixtures_exist(codec: PxFrameCodec) -> None:
    """PC-109: both vendored chain fixtures (`connected`, `with-gap`) are present."""
    del codec
    assert set(_chain_fixture_names()) == {"connected", "with-gap"}


@pytest.mark.parametrize("codec", BINDINGS, ids=_binding_id)
@pytest.mark.parametrize("name", _chain_fixture_names())
def test_chain_fixture_builds_to_its_sidecar(name: str, codec: PxFrameCodec) -> None:
    """PC-109: the chain built from a fixture's member frames matches its `chain.json` exactly."""
    fixture_dir = _CHAINS_DIR / name
    chain_json = json.loads((fixture_dir / "chain.json").read_text(encoding="utf-8"))

    members = []
    for pxf_path in fixture_dir.glob("*.pxf"):
        result = codec.decode(pxf_path.read_bytes())
        assert isinstance(result, PxFrameAccepted), f"{name}/{pxf_path.name}: expected accepted, got {result!r}"
        members.append(PxChainMember(header=result.frame.header, frame_hash=result.frame.frame_hash))

    built = codec.build_chain(members)
    assert isinstance(built, PxChainBuilt), f"{name}: expected a built chain, got {built!r}"
    chain = built.chain

    assert chain.is_sealed == chain_json["sealed"]
    assert chain.is_connected == chain_json["connected"]
    assert chain.reach == int(chain_json["reach"])
    assert [member.header.frame_id for member in chain.walk] == [int(fid) for fid in chain_json["walk"]]
    assert [(gap.range_from, gap.range_to) for gap in chain.gaps] == [
        (int(gap["from"]), int(gap["to"])) for gap in chain_json["gaps"]
    ]

    expected_hash = chain_json.get("sequenceHash")
    if expected_hash is not None:
        computed = codec.compute_sequence_hash(chain.body_frame_hashes_in_walk_order)
        assert computed.hex() == expected_hash
