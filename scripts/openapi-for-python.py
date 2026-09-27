"""Rewrites the pinned OpenAPI document into the shape openapi-python-client can generate from.

Two reshapes:

1. The three look-up multipart bodies (`/lookup`, `/lookup/slots/{lookupSlotId}/queries`,
   `/sequences/{sequenceId}/frames`) declare their image parts as `additionalProperties` (the part
   name carries no meaning), which the generator turns into invalid Python. Those bodies become a
   plain object with one repeatable `image` part; the hand-written layer sends the parts itself.
2. PC-110: any path template name an operation does not already declare `in: path` (at the
   operation or path-item level) gets declared as a required string path parameter, derived from
   the template itself. The sequence routes never declare `sequenceId` (the server's ticket filter
   reads it from route values instead), which otherwise makes openapi-python-client refuse those
   operations with "Incorrect path templating" and skip them.

Everything else passes through untouched.
"""
import json
import re
import sys

_TEMPLATE_NAME = re.compile(r"\{([^}]+)\}")


def _declared_path_param_names(item: dict, op: dict) -> set:
    """PC-110: the names already declared `in: path`, at path-item or operation level."""
    names = set()
    for params in (item.get("parameters", []), op.get("parameters", [])):
        for param in params:
            if param.get("in") == "path":
                names.add(param["name"])
    return names


def _add_missing_path_parameters(path: str, item: dict, op: dict) -> None:
    """PC-110: declare every template name the operation does not already declare as path."""
    template_names = _TEMPLATE_NAME.findall(path)
    if not template_names:
        return
    declared = _declared_path_param_names(item, op)
    missing = [name for name in template_names if name not in declared]
    if not missing:
        return
    # PC-110: rework - append in template order rather than inserting at 0, which reversed it
    params = op.setdefault("parameters", [])
    for name in missing:
        params.append({"name": name, "in": "path", "required": True, "schema": {"type": "string"}})


src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    doc = json.load(f)
for path, item in doc["paths"].items():
    for method, op in item.items():
        if method not in ("get", "post", "put", "delete", "patch"):
            continue
        # PC-110: declare any template name the pinned document omits, before the multipart reshape
        _add_missing_path_parameters(path, item, op)
        content = op.get("requestBody", {}).get("content", {})
        mp = content.get("multipart/form-data")
        if not mp:
            continue
        schema = mp.get("schema", {})
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict) and "properties" not in schema:
            schema.pop("additionalProperties")
            schema["properties"] = {"image": extra}
with open(dst, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
