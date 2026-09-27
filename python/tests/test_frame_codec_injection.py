"""The PX Frame seam at the route level: default resolution, a non-codec's refusal, and who may
import the pure binding at all; plus the register-conversation injection case, a `FakeCodec`
driving `register_sequence` end to end.

The route-level cases (the resolution rule itself and the seam's import graph, walked with `ast`
rather than a hand-maintained list of modules) are PC-113's; the register case at the bottom of
this file is PC-114's.
"""

from __future__ import annotations

import ast
import base64
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import respx
from xio_parallax_client import AsyncParallaxClient, ParallaxClient, ParallaxClientOptions
from xio_parallax_client.frames.binding import DefaultPxFrameCodec, default_frame_codec, resolve_frame_codec
from xio_parallax_client.frames.protocol import EncodedPxFrame, PxFrame, PxFrameAccepted, PxHeadHeader

from .conftest import BASE_URL
from .sequence_server import multipart_parts
from .test_register_sequence import register_options, source

_PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "xio_parallax_client"
_PACKAGE_NAME = "xio_parallax_client"


def _iter_source_files() -> list[Path]:
    """Every `.py` file this package ships, excluding the generated client (never edited, never checked)."""
    return [
        path
        for path in sorted(_PACKAGE_ROOT.rglob("*.py"))
        if "generated" not in path.relative_to(_PACKAGE_ROOT).parts
    ]


def _module_dotted_name(path: Path) -> str:
    """The dotted module name a source file under the package root corresponds to."""
    parts = list(path.relative_to(_PACKAGE_ROOT.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _owning_package(path: Path, module_name: str) -> str:
    """The dotted package a relative import in `path` (named `module_name`) resolves against."""
    return module_name if path.name == "__init__.py" else module_name.rsplit(".", 1)[0]


def _resolved_imports(path: Path) -> list[str]:
    """Every dotted name this file imports: absolute names as written, relative ones resolved
    against the file's own package. `from x import name` yields both `x` and `x.name`, since a
    submodule can be reached either way (`from ..frames import binding` imports the module named
    `binding` exactly as `from ..frames.binding import ...` does)."""
    module_name = _module_dotted_name(path)
    package = _owning_package(path, module_name)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    resolved: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            resolved.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                parts = package.split(".") if package else []
                if node.level > 1:
                    parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join(parts)
                base = f"{base}.{node.module}" if base and node.module else (node.module or base)
            resolved.append(base)
            resolved.extend(f"{base}.{alias.name}" for alias in node.names)
    return resolved


def _files_importing(prefix: str, *, excluding: set[Path]) -> list[Path]:
    """Every source file, other than `excluding`, whose imports name `prefix` or a name under it."""
    return [
        path
        for path in _iter_source_files()
        if path not in excluding
        and any(name == prefix or name.startswith(f"{prefix}.") for name in _resolved_imports(path))
    ]


# PC-113: the import-graph test the seam's design calls for; no hand-maintained module list
def test_only_binding_imports_the_pure_codec() -> None:
    """`frames/binding.py` is the only module outside `frames/pure/` itself that imports it."""
    pure_dir = _PACKAGE_ROOT / "frames" / "pure"
    excluding = {_PACKAGE_ROOT / "frames" / "binding.py"} | set(pure_dir.rglob("*.py"))
    assert _files_importing(f"{_PACKAGE_NAME}.frames.pure", excluding=excluding) == []


# PC-113: the conversation depends on the seam's protocol only, never a concrete binding
def test_sequences_never_import_a_binding() -> None:
    """Nothing under `sequences/` imports `frames.pure` or `frames.binding`."""
    sequences_files = set((_PACKAGE_ROOT / "sequences").rglob("*.py"))
    offenders: set[Path] = set()
    for prefix in (f"{_PACKAGE_NAME}.frames.pure", f"{_PACKAGE_NAME}.frames.binding"):
        offenders.update(_files_importing(prefix, excluding=set()))
    assert offenders & sequences_files == set()


# PC-113: rework - assert against the binding's own default type, not the pure codec directly,
# so swapping frames/binding.py's import line changes no test
def test_default_codec_is_the_binding_line() -> None:
    """`resolve_frame_codec(None)` and `default_frame_codec()` both answer the binding's default."""
    assert isinstance(resolve_frame_codec(None), DefaultPxFrameCodec)
    assert isinstance(default_frame_codec(), DefaultPxFrameCodec)


# PC-113: rework - assert against the binding's own default type, not the pure codec directly
def test_client_frame_codec_defaults_to_the_binding(options: ParallaxClientOptions) -> None:
    """Both clients resolve `frame_codec=None` to the default binding, held as `client.frame_codec`."""
    assert isinstance(ParallaxClient(options).frame_codec, DefaultPxFrameCodec)
    assert isinstance(AsyncParallaxClient(options).frame_codec, DefaultPxFrameCodec)


def test_a_non_codec_is_refused_naming_every_missing_member() -> None:
    """`resolve_frame_codec` raises `TypeError` naming every `PxFrameCodec` member a bad object lacks."""

    class NotACodec:
        """An object implementing none of `PxFrameCodec`."""

    with pytest.raises(TypeError) as excinfo:
        resolve_frame_codec(NotACodec())
    message = str(excinfo.value)
    for member in ("format_version", "encode", "decode", "build_chain", "compute_sequence_hash"):
        assert member in message


def test_a_partial_codec_names_only_what_it_is_missing() -> None:
    """A near-codec is refused naming only the members it actually lacks."""

    class PartialCodec:
        """Has `format_version`, `encode` and `decode`, but neither chain member."""

        format_version = 1

        def encode(self, header: object, buckets: object) -> object:
            raise NotImplementedError

        def decode(self, frame: object) -> object:
            raise NotImplementedError

    with pytest.raises(TypeError) as excinfo:
        resolve_frame_codec(PartialCodec())
    message = str(excinfo.value)
    assert "build_chain" in message
    assert "compute_sequence_hash" in message
    assert "encode" not in message
    assert "decode" not in message


def test_a_full_duck_typed_codec_is_used_unchanged(options: ParallaxClientOptions) -> None:
    """An object with every `PxFrameCodec` member satisfies the protocol and is passed through as is."""

    class FakeCodec:
        """Implements every `PxFrameCodec` member, none of them for real."""

        format_version = 99

        def encode(self, header: object, buckets: object) -> object:
            raise NotImplementedError

        def decode(self, frame: object) -> object:
            raise NotImplementedError

        def build_chain(self, members: object) -> object:
            raise NotImplementedError

        def compute_sequence_hash(self, body_frame_hashes: object) -> object:
            raise NotImplementedError

    fake = FakeCodec()
    client = ParallaxClient(options, frame_codec=fake)
    assert client.frame_codec is fake


# PC-114: a codec whose bytes are legible, so a register conversation's own bytes can be asserted directly
class FakeSequenceCodec:
    """Implements `PxFrameCodec`; `encode` answers `b"FAKE:<type>:<id>:<prev>"`, `decode` answers
    any bytes as a HEAD frame with id 7, regardless of what was actually encoded."""

    format_version = 1

    def encode(self, header: object, buckets: object) -> EncodedPxFrame:
        """Encode a legible marker instead of a real PX Frame: type, id and prev, `buckets` unused."""
        prev = getattr(header, "prev", None)
        frame = f"FAKE:{header.frame_type.name}:{header.frame_id}:{prev}".encode()
        return EncodedPxFrame(frame, frame_hash=frame.ljust(32, b"\x00")[:32])

    def decode(self, frame: bytes) -> PxFrameAccepted:
        """Decode any bytes as a HEAD frame with id 7; open's HEAD decode is the only caller here."""
        header = PxHeadHeader(uuid4(), 7)
        return PxFrameAccepted(PxFrame(header=header, buckets=(), frame_hash=b"\x00" * 32))

    def build_chain(self, members: object) -> object:
        raise NotImplementedError

    def compute_sequence_hash(self, body_frame_hashes: object) -> object:
        raise NotImplementedError


@respx.mock
def test_register_sequence_uses_only_the_injected_codec(options: ParallaxClientOptions) -> None:
    """`register_sequence` reads HEAD's id through the injected codec alone (7, not the real one)
    and every uploaded part's bytes are exactly the fake codec's, never the default binding's."""
    sequence_id = uuid4()
    respx.post(f"{BASE_URL}/sequences").mock(
        return_value=httpx.Response(
            201,
            json={
                "sequenceId": str(sequence_id),
                "ticket": "sequence-ticket-fake-codec",
                "headFrame": base64.b64encode(b"whatever a real decoder would refuse").decode("ascii"),
            },
        )
    )

    def frames_side_effect(request: httpx.Request) -> httpx.Response:
        parts = multipart_parts(request)
        ids = [int(name) for name, _ in parts]
        verdict = None
        if 9 in ids:
            verdict = {
                "state": "sealed",
                "framesReceived": 9,
                "expectedSize": None,
                "reach": 9,
                "gaps": [],
                "errata": [],
                "connected": True,
            }
        return httpx.Response(201, json={"frames": [{"frameId": i, "errata": False} for i in ids], "verdict": verdict})

    respx.post(f"{BASE_URL}/sequences/{sequence_id}/frames").mock(side_effect=frames_side_effect)
    respx.post(f"{BASE_URL}/sequences/{sequence_id}/commit").mock(
        return_value=httpx.Response(
            200,
            json={
                "sequenceHash": "sequence-hash",
                "outcome": "registered",
                "sequenceRecordPublished": True,
                "frames": [{"frameId": 1, "state": "published", "originalImageHash": None, "refusalName": None}],
            },
        )
    )
    respx.get(f"{BASE_URL}/sequences/{sequence_id}/results").mock(
        return_value=httpx.Response(
            200,
            json={
                "sequenceHash": "sequence-hash",
                "outcome": "registered",
                "finalSize": 1,
                "committedAt": "2026-09-27T00:00:00Z",
            },
        )
    )

    client = ParallaxClient(options, frame_codec=FakeSequenceCodec())

    result = client.register_sequence(source(8), register_options(max_frames_per_request=8))

    frames_calls = [call for call in respx.calls if call.request.url.path == f"/sequences/{sequence_id}/frames"]
    first_batch = multipart_parts(frames_calls[0].request)
    second_batch = multipart_parts(frames_calls[1].request)
    assert first_batch == [("8", b"FAKE:BODY:8:7")]
    assert second_batch == [("9", b"FAKE:END:9:8")]
    assert result.commit.outcome == "registered"
