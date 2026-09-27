"""Smoke test for `examples/python/sequence_from_images.py`: its main path against the fake
sequence conversation server, over a temporary directory of small generated images.

Mirrors what `RegisterSequenceTests` proves for the conversation itself, at the example's altitude:
the directory becomes one frame per file in name order, sent as BODY then END, and the printed
result names the sequence hash, outcome, final size and the look-up match.
"""

# PC-115: the example's smoke test, run against the fake conversation server

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest
import respx

from .conftest import BASE_URL
from .sequence_server import SequenceConversationServer
from .test_register_sequence import commit_response, verdict_json

_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "python" / "sequence_from_images.py"


def _load_example() -> ModuleType:
    """Import the example script as a module, since it lives outside the package."""
    spec = importlib.util.spec_from_file_location("sequence_from_images_example", _EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_images(directory: Path, count: int) -> None:
    """Writes `count` small PNG-named files under `directory`, named so ordinal order is 1..count."""
    for index in range(1, count + 1):
        (directory / f"img{index}.png").write_bytes(bytes([index, index, index]))


@respx.mock
def test_main_registers_the_directory_and_prints_the_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _make_images(tmp_path, 3)

    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=4)
    server.commits.append(commit_response("registered", "published", "published", "published"))
    respx.post(f"{BASE_URL}/lookup").mock(
        return_value=httpx.Response(200, json={"matched": True, "matchedOriginalImageHashes": ["h"], "candidates": []})
    )

    monkeypatch.setenv("PARALLAX_BASE_URL", BASE_URL)
    monkeypatch.setenv("PARALLAX_TOKEN", "test-token")
    monkeypatch.setenv("PARALLAX_IMAGES", str(tmp_path))
    monkeypatch.setenv("PARALLAX_FRAME_INTERVAL_MS", "40")
    monkeypatch.setenv("PARALLAX_MAX_REQUEST_BYTES", "1000000")
    monkeypatch.setenv("PARALLAX_MAX_FRAMES_PER_REQUEST", "8")

    example = _load_example()
    example.main()

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [
        "POST /sequences",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/commit",
        f"GET {prefix}/results",
    ]
    batches = server.decode_uploads()
    assert len(batches) == 2
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in batches[0]] == [
        ("BODY", 1, 0, 2),
        ("BODY", 2, 1, 3),
        ("BODY", 3, 2, 4),
    ]
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in batches[1]] == [("END", 4, 3, None)]

    out = capsys.readouterr().out
    assert "sequence hash: sequence-hash" in out
    assert "outcome: registered" in out
    assert "final size: 3" in out
    assert "lookup matched: True" in out
    assert "test-token" not in out


def test_main_refuses_a_missing_required_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_images(tmp_path, 1)
    monkeypatch.delenv("PARALLAX_TOKEN", raising=False)
    monkeypatch.setenv("PARALLAX_IMAGES", str(tmp_path))
    monkeypatch.setenv("PARALLAX_FRAME_INTERVAL_MS", "40")
    monkeypatch.setenv("PARALLAX_MAX_REQUEST_BYTES", "1000000")
    monkeypatch.setenv("PARALLAX_MAX_FRAMES_PER_REQUEST", "8")

    example = _load_example()
    with pytest.raises(SystemExit) as excinfo:
        example.main()
    assert "PARALLAX_TOKEN" in str(excinfo.value)


def test_main_refuses_an_unrecognised_file_extension(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "notes.txt").write_bytes(b"not an image")
    monkeypatch.setenv("PARALLAX_TOKEN", "test-token")
    monkeypatch.setenv("PARALLAX_IMAGES", str(tmp_path))
    monkeypatch.setenv("PARALLAX_FRAME_INTERVAL_MS", "40")
    monkeypatch.setenv("PARALLAX_MAX_REQUEST_BYTES", "1000000")
    monkeypatch.setenv("PARALLAX_MAX_FRAMES_PER_REQUEST", "8")

    example = _load_example()
    with pytest.raises(SystemExit) as excinfo:
        example.main()
    assert "notes.txt" in str(excinfo.value)
