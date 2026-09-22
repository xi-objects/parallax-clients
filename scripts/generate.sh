#!/usr/bin/env sh
# Regenerates both clients from openapi/v1.json. CI runs this and fails on any diff.
set -eu
cd "$(dirname "$0")/.."
kiota generate -l CSharp -d openapi/v1.json -c ParallaxApiClient -n Xio.Parallax.Client.Generated \
  -o src/Xio.Parallax.Client/Generated --exclude-backward-compatible --clean-output
tmp="$(mktemp -t openapi-python.XXXXXX.json)"
python scripts/openapi-for-python.py openapi/v1.json "$tmp"
uvx --from openapi-python-client openapi-python-client generate --path "$tmp" \
  --config openapi-python-client.yaml --meta none \
  --output-path python/xio_parallax_client/generated --overwrite
rm -f "$tmp"
