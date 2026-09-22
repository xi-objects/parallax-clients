"""Exit 0 when two OpenAPI documents are the same contract, 1 when they differ.

`info.version` carries the build commit as semver build metadata, which changes on every deploy
without changing the contract, so that part is ignored.
"""
import json
import sys


def normalized(path: str) -> dict:
    doc = json.load(open(path, encoding="utf-8"))
    version = doc.get("info", {}).get("version", "")
    doc.setdefault("info", {})["version"] = version.split("+", 1)[0]
    return doc


sys.exit(0 if normalized(sys.argv[1]) == normalized(sys.argv[2]) else 1)
