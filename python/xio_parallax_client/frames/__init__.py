"""The PX Frame seam and the frame source seam.

`PxFrameCodec` (in `protocol.py`) is the only thing the client and the sequence conversation know
about the PX Frame format; a binding implements it. `SequenceFrameSource` and
`AsyncSequenceFrameSource` (in `source.py`) are what a later ingestion implements to hand the
client a sequence's frames.
"""

# PC-107: the seam's public names, re-exported once, plus the default binding's resolution

from .binding import default_frame_codec, resolve_frame_codec
from .protocol import (
    IMAGE_BUCKET_TAG,
    EncodedPxFrame,
    PxBodyHeader,
    PxBucket,
    PxBucketContent,
    PxBucketEntry,
    PxChain,
    PxChainBuildResult,
    PxChainBuilt,
    PxChainMember,
    PxChainRefusal,
    PxChainRefused,
    PxEndHeader,
    PxFrame,
    PxFrameAccepted,
    PxFrameCodec,
    PxFrameEncodeError,
    PxFrameHeader,
    PxFrameReadResult,
    PxFrameRefusal,
    PxFrameRefused,
    PxFrameType,
    PxGapHeader,
    PxGapRange,
    PxHeadHeader,
    PxPresenceFlags,
)
from .source import AsyncSequenceFrameSource, SequenceFrameInput, SequenceFrameSource

__all__ = [
    "IMAGE_BUCKET_TAG",
    "AsyncSequenceFrameSource",
    "EncodedPxFrame",
    "PxBodyHeader",
    "PxBucket",
    "PxBucketContent",
    "PxBucketEntry",
    "PxChain",
    "PxChainBuildResult",
    "PxChainBuilt",
    "PxChainMember",
    "PxChainRefusal",
    "PxChainRefused",
    "PxEndHeader",
    "PxFrame",
    "PxFrameAccepted",
    "PxFrameCodec",
    "PxFrameEncodeError",
    "PxFrameHeader",
    "PxFrameReadResult",
    "PxFrameRefusal",
    "PxFrameRefused",
    "PxFrameType",
    "PxGapHeader",
    "PxGapRange",
    "PxHeadHeader",
    "PxPresenceFlags",
    "SequenceFrameInput",
    "SequenceFrameSource",
    "default_frame_codec",
    "resolve_frame_codec",
]
