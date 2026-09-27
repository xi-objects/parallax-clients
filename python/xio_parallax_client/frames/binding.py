"""THE one line naming the default PX Frame codec binding, and how a caller-given one is resolved.

Swapping the default binding package-wide is changing the one import below; per-client, a caller
passes its own `frame_codec=` instead. See `python-sequences-design.md` section (b).
"""

from __future__ import annotations

import typing

from .protocol import PxFrameCodec

# PC-107: the default binding, swapped by changing this one import line
from .pure import PurePxFrameCodec as DefaultPxFrameCodec


def _protocol_member_names(protocol: type) -> frozenset[str]:
    """PC-107: the member names `protocol` declares, read from the protocol itself.

    Python 3.13 exposes `typing.get_protocol_members`; on 3.11/3.12, where it does not exist yet,
    the interpreter computes the same set on the class as `__protocol_attrs__`. Either branch reads
    it from the protocol, never from a hand-kept copy, so a member added to `PxFrameCodec` changes
    nothing here.
    """
    get_members = getattr(typing, "get_protocol_members", None)
    if get_members is not None:
        return frozenset(get_members(protocol))
    return frozenset(protocol.__protocol_attrs__)  # type: ignore[attr-defined]


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

    missing = [name for name in sorted(_protocol_member_names(PxFrameCodec)) if not hasattr(frame_codec, name)]
    raise TypeError(f"frame_codec does not implement PxFrameCodec: missing {', '.join(missing)}")
