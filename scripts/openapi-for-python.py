"""Rewrites the pinned OpenAPI document into the shape openapi-python-client can generate from.

The two look-up multipart bodies declare their image parts as `additionalProperties` (the part
name carries no meaning), which the generator turns into invalid Python. Those bodies become a
plain object with one repeatable `image` part; the hand-written layer sends the parts itself.
Everything else passes through untouched.
"""
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
doc = json.load(open(src, encoding="utf-8"))
for path, item in doc["paths"].items():
    for method, op in item.items():
        if method not in ("get", "post", "put", "delete", "patch"):
            continue
        content = op.get("requestBody", {}).get("content", {})
        mp = content.get("multipart/form-data")
        if not mp:
            continue
        schema = mp.get("schema", {})
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict) and "properties" not in schema:
            schema.pop("additionalProperties")
            schema["properties"] = {"image": extra}
json.dump(doc, open(dst, "w", encoding="utf-8"), indent=2)
