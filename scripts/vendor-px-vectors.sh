#!/bin/sh
# PC-109: vendor the PX Frame test vectors from xio_parallax_common, unmodified, byte for byte.
#
# Usage: scripts/vendor-px-vectors.sh <path-to-xio_parallax_common-checkout>
#
# Copies vectors/frames and vectors/chains from the given checkout (at its current HEAD) into
# python/tests/vectors/px-frame, deleting stale files there first, and rewrites VECTORS.md from a
# template with the source commit read from the checkout itself, never typed by hand.

set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-xio_parallax_common-checkout>" >&2
    exit 1
fi

common_checkout="$1"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
dest_dir="$repo_root/python/tests/vectors/px-frame"

if [ ! -d "$common_checkout/vectors/frames" ] || [ ! -d "$common_checkout/vectors/chains" ]; then
    echo "error: $common_checkout does not look like an xio_parallax_common checkout (no vectors/frames or vectors/chains)" >&2
    exit 1
fi

commit_sha="$(git -C "$common_checkout" rev-parse HEAD)"

rm -rf "$dest_dir/frames" "$dest_dir/chains"
mkdir -p "$dest_dir/frames" "$dest_dir/chains"

cp -a "$common_checkout/vectors/frames/." "$dest_dir/frames/"
cp -a "$common_checkout/vectors/chains/." "$dest_dir/chains/"

frame_pxf_count="$(find "$dest_dir/frames" -name '*.pxf' | wc -l | tr -d ' ')"
chain_file_count="$(find "$dest_dir/chains" -type f | wc -l | tr -d ' ')"
total_file_count="$(find "$dest_dir/frames" "$dest_dir/chains" -type f | wc -l | tr -d ' ')"
vendored_date="$(date -u +%Y-%m-%d)"

cat > "$dest_dir/VECTORS.md" <<EOF
# PX Frame test vectors

Vendored unmodified from \`xio_parallax_common\`'s \`vectors/\` directory. These are XI Objects' own
test vectors, redistributed as-is; they are not under this repository's MIT license.

- **Source repository:** \`xio_parallax_common\`
- **Source path:** \`vectors/\`
- **Source commit:** \`$commit_sha\`
- **Vendored on:** $vendored_date
- **File count:** $total_file_count ($frame_pxf_count frame vectors x 2 files, $chain_file_count chain fixture files)
- **Refresh command:** \`scripts/vendor-px-vectors.sh <path-to-xio_parallax_common-checkout>\`

No test reads this file; it is a record for a person, not a fixture.
EOF

echo "vendored $total_file_count files from $common_checkout at $commit_sha into $dest_dir"
