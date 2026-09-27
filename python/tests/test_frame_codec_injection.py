"""The PX Frame seam at the route level: default resolution, a non-codec's refusal, and who may
import the pure binding at all.

The register-conversation injection case (a `FakeCodec` driving `register_sequence` end to end)
lands with PC-114; this file covers what PC-113 owns: the resolution rule itself and the seam's
import graph, walked with `ast` rather than a hand-maintained list of modules.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from xio_parallax_client import AsyncParallaxClient, ParallaxClient, ParallaxClientOptions
from xio_parallax_client.frames.binding import default_frame_codec, resolve_frame_codec
from xio_parallax_client.frames.pure import PurePxFrameCodec

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


def test_default_codec_is_the_binding_line() -> None:
    """`resolve_frame_codec(None)` and `default_frame_codec()` both answer the binding's default."""
    assert isinstance(resolve_frame_codec(None), PurePxFrameCodec)
    assert isinstance(default_frame_codec(), PurePxFrameCodec)


def test_client_frame_codec_defaults_to_the_binding(options: ParallaxClientOptions) -> None:
    """Both clients resolve `frame_codec=None` to the default binding, held as `client.frame_codec`."""
    assert isinstance(ParallaxClient(options).frame_codec, PurePxFrameCodec)
    assert isinstance(AsyncParallaxClient(options).frame_codec, PurePxFrameCodec)


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
