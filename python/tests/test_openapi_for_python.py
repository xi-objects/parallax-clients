"""PC-110: the generator reshape declares undeclared path template names as string path parameters."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "openapi-for-python.py"


def _reshape(doc: dict, tmp_path: Path) -> dict:
    """Runs the script's own reshape over an in-memory document, via its file entry point."""
    src = tmp_path / "src.json"
    dst = tmp_path / "dst.json"
    src.write_text(json.dumps(doc), encoding="utf-8")
    module_spec = importlib.util.spec_from_file_location("openapi_for_python_main", _SCRIPT_PATH)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)

    old_argv = sys.argv
    sys.argv = ["openapi-for-python.py", str(src), str(dst)]
    try:
        module_spec.loader.exec_module(module)
    finally:
        sys.argv = old_argv
    return json.loads(dst.read_text(encoding="utf-8"))


def _minimal_doc(paths: dict) -> dict:
    return {
        "openapi": "3.0.3",
        "info": {"title": "t", "version": "1"},
        "paths": paths,
    }


def test_undeclared_template_names_become_string_path_parameters(tmp_path: Path) -> None:
    doc = _minimal_doc(
        {
            "/sequences/{sequenceId}/gaps": {
                "get": {
                    "parameters": [{"name": "X-Sequence-Ticket", "in": "header", "required": True}],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    out = _reshape(doc, tmp_path)
    params = out["paths"]["/sequences/{sequenceId}/gaps"]["get"]["parameters"]
    path_params = [p for p in params if p["in"] == "path"]
    assert path_params == [{"name": "sequenceId", "in": "path", "required": True, "schema": {"type": "string"}}]
    header_params = [p for p in params if p["in"] == "header"]
    assert header_params == [{"name": "X-Sequence-Ticket", "in": "header", "required": True}]


def test_declared_path_parameters_are_left_alone(tmp_path: Path) -> None:
    doc = _minimal_doc(
        {
            "/slots/{slotId}/uploads": {
                "post": {
                    "parameters": [{"name": "slotId", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        }
    )
    out = _reshape(doc, tmp_path)
    params = out["paths"]["/slots/{slotId}/uploads"]["post"]["parameters"]
    assert params == [{"name": "slotId", "in": "path", "required": True, "schema": {"type": "string"}}]


def test_path_item_level_declaration_is_also_respected(tmp_path: Path) -> None:
    doc = _minimal_doc(
        {
            "/sequences/{sequenceId}/frames/{frameId}": {
                "parameters": [{"name": "sequenceId", "in": "path", "required": True, "schema": {"type": "string"}}],
                "delete": {
                    "parameters": [{"name": "frameId", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "ok"}},
                },
            }
        }
    )
    out = _reshape(doc, tmp_path)
    params = out["paths"]["/sequences/{sequenceId}/frames/{frameId}"]["delete"]["parameters"]
    path_names = sorted(p["name"] for p in params if p["in"] == "path")
    assert path_names == ["frameId"]


def test_every_sequence_operation_is_generated(tmp_path: Path) -> None:
    repo_root = _SCRIPT_PATH.parents[1]
    doc = json.loads((repo_root / "openapi" / "v1.json").read_text(encoding="utf-8"))
    out = _reshape(doc, tmp_path)
    for path, item in doc["paths"].items():
        if "/sequences" not in path:
            continue
        for method in item:
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            template_names = set(re.findall(r"\{([^}]+)\}", path))
            reshaped_params = out["paths"][path][method].get("parameters", [])
            declared = {p["name"] for p in reshaped_params if p["in"] == "path"}
            assert template_names <= declared, f"{method} {path} missing {template_names - declared}"
