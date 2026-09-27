"""`PurePxFrameCodec`: the in-repo pure-Python binding of `PxFrameCodec`.

Composes `_encoder.py`, `_reader.py` (this story, PC-107) and `_chain.py` (PC-108) into the one
protocol the client and the sequence conversation depend on. Nothing outside `frames/binding.py`
imports this package (`test_only_binding_imports_the_pure_codec` guarantees it), so a future
library or native shim replaces it by changing that one import line.
"""

# PC-107: PurePxFrameCodec, composing the pure-Python encoder, reader and chain builder

from __future__ import annotations

from collections.abc import Collection, Sequence

from ..protocol import (
    EncodedPxFrame,
    PxBucketContent,
    PxChainBuildResult,
    PxChainMember,
    PxFrameHeader,
    PxFrameReadResult,
)
from ._chain import build_chain as _build_chain
from ._chain import compute_sequence_hash as _compute_sequence_hash
from ._encoder import encode as _encode
from ._layout import FORMAT_VERSION
from ._reader import decode as _decode


class PurePxFrameCodec:
    """The pure-Python `PxFrameCodec` binding: no native dependency beyond the pinned `blake3` package."""

    @property
    def format_version(self) -> int:
        """The one format version this binding reads and writes."""
        return FORMAT_VERSION

    def encode(self, header: PxFrameHeader, buckets: Sequence[PxBucketContent]) -> EncodedPxFrame:
        """Encode one frame and its frame hash; raises `PxFrameEncodeError` for input the reader would refuse."""
        return _encode(header, buckets)

    def decode(self, frame: bytes) -> PxFrameReadResult:
        """Read exactly one frame, checking the format's rules in order."""
        return _decode(frame)

    def build_chain(self, members: Collection[PxChainMember]) -> PxChainBuildResult:
        """Build one chain from members in any order, or answer the first chain rule broken."""
        return _build_chain(members)

    def compute_sequence_hash(self, body_frame_hashes: Sequence[bytes]) -> bytes:
        """BLAKE3-256 over the BODY frame hashes concatenated in the order given."""
        return _compute_sequence_hash(body_frame_hashes)


__all__ = ["PurePxFrameCodec"]
