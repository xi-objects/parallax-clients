#!/bin/sh
# PC-109: vendor the PX Frame test vectors from xio_parallax_common, unmodified, byte for byte.
#
# Usage: scripts/vendor-px-vectors.sh <path-to-xio_parallax_common-checkout> <sha>
#
# Exports vectors/frames and vectors/chains at the given, already-committed SHA with `git archive`
# (never the checkout's working tree, which a dirty tree would otherwise vendor under a SHA that
# does not hold those bytes) into python/tests/vectors/px-frame, deleting stale files there first,
# and rewrites VECTORS.md from a template with the given commit, never read back from the tree.
# PC-119: and vectors/sequence-hash and vectors/sequence-summary too, when the commit carries them (the sequence
# summary preimage the sequence-record verifiers in both clients are proven against); an older commit has neither.

set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <path-to-xio_parallax_common-checkout> <sha>" >&2
    exit 1
fi

common_checkout="$1"
commit_sha="$2"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
dest_dir="$repo_root/python/tests/vectors/px-frame"

if ! commit_sha="$(git -C "$common_checkout" rev-parse --verify --quiet "$commit_sha^{commit}")"; then
    echo "error: $2 does not resolve to a commit in $common_checkout" >&2
    exit 1
fi

export_dir="$(mktemp -d)"
trap 'rm -rf "$export_dir"' EXIT

git -C "$common_checkout" archive "$commit_sha" vectors | tar -x -C "$export_dir"

if [ ! -d "$export_dir/vectors/frames" ] || [ ! -d "$export_dir/vectors/chains" ]; then
    echo "error: $commit_sha in $common_checkout does not look like an xio_parallax_common commit (no vectors/frames or vectors/chains)" >&2
    exit 1
fi

rm -rf "$dest_dir/frames" "$dest_dir/chains" "$dest_dir/sequence-hash" "$dest_dir/sequence-summary"
mkdir -p "$dest_dir/frames" "$dest_dir/chains"

cp -a "$export_dir/vectors/frames/." "$dest_dir/frames/"
cp -a "$export_dir/vectors/chains/." "$dest_dir/chains/"

# PC-119: the sequence vectors, when this commit carries them
for sequence_dir in sequence-hash sequence-summary; do
    if [ -d "$export_dir/vectors/$sequence_dir" ]; then
        mkdir -p "$dest_dir/$sequence_dir"
        cp -a "$export_dir/vectors/$sequence_dir/." "$dest_dir/$sequence_dir/"
    fi
done

frame_pxf_count="$(find "$dest_dir/frames" -name '*.pxf' | wc -l | tr -d ' ')"
chain_file_count="$(find "$dest_dir/chains" -type f | wc -l | tr -d ' ')"
sequence_file_count="$(find "$dest_dir" -path "$dest_dir/sequence-*" -type f | wc -l | tr -d ' ')"
total_file_count="$(find "$dest_dir/frames" "$dest_dir/chains" -type f | wc -l | tr -d ' ')"
total_file_count="$((total_file_count + sequence_file_count))"
vendored_date="$(date -u +%Y-%m-%d)"

cat > "$dest_dir/VECTORS.md" <<EOF
# PX Frame test vectors

Vendored unmodified from \`xio_parallax_common\`'s \`vectors/\` directory. These are XI Objects' own
test vectors, redistributed as-is; they are not under this repository's MIT license.

- **Source repository:** \`xio_parallax_common\`
- **Source path:** \`vectors/\`
- **Source commit:** \`$commit_sha\`
- **Vendored on:** $vendored_date
- **File count:** $total_file_count ($frame_pxf_count frame vectors x 2 files, $chain_file_count chain fixture files, $sequence_file_count sequence-hash and sequence-summary vectors)
- **Refresh command:** \`scripts/vendor-px-vectors.sh <path-to-xio_parallax_common-checkout> <sha>\`

No test reads this file; it is a record for a person, not a fixture.
EOF

echo "vendored $total_file_count files from $common_checkout at $commit_sha into $dest_dir"
