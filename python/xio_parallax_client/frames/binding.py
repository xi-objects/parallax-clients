"""THE one line naming the default PX Frame codec binding, and how a caller-given one is resolved.

Swapping the default binding package-wide is changing the one import below; per-client, a caller
passes its own `frame_codec=` instead. See `python-sequences-design.md` section (b).
"""

from __future__ import annotations

from .protocol import PxFrameCodec

# PC-107: the default binding, swapped by changing this one import line
from .pure import PurePxFrameCodec as DefaultPxFrameCodec

_PROTOCOL_MEMBERS = ("format_version", "encode", "decode", "build_chain", "compute_sequence_hash")


def default_frame_codec() -> PxFrameCodec:
    """A fresh instance of the default PX Frame codec binding."""
    return DefaultPxFrameCodec()


def resolve_frame_codec(frame_codec: PxFrameCodec | None) -> PxFrameCodec:
    """Resolve a caller-given codec, or the default binding when `None`.

    Raises `TypeError` naming every `PxFrameCodec` member a non-`None` codec is missing.
    """
    if frame_codec is None:
        return default_frame_codec()
    if isinstance(frame_codec, PxFrameCodec):
        return frame_codec

    missing = [name for name in _PROTOCOL_MEMBERS if not hasattr(frame_codec, name)]
    raise TypeError(f"frame_codec does not implement PxFrameCodec: missing {', '.join(missing)}")
