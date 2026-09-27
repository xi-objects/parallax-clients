"""Encodes sequence frames through an injected `PxFrameCodec`; no PX Frame format logic here.

Mirrors the .NET client's `SequenceFrameEncoder`: it composes a codec once and turns the sequence
conversation's frames into wire bytes, and reads a HEAD frame's id back. Every byte comes from the
codec; this module only shapes the calls.
"""

# PC-112: the sequence conversation's one point of contact with an injected PxFrameCodec

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from ..frames.protocol import (
    PxBodyHeader,
    PxEndHeader,
    PxFrameAccepted,
    PxFrameCodec,
    PxFrameType,
    PxHeadHeader,
)
from ..frames.source import SequenceFrameInput
from .models import EncodedFrame  # PC-111: EncodedFrame's home; re-exported here for PC-112's callers

_MICROSECOND = timedelta(microseconds=1)


# PC-112: composes an injected codec for the frames a sequence conversation sends and reads
class SequenceFrameEncoder:
    """Encodes BODY and END sequence frames, and reads a HEAD frame's id, through one `PxFrameCodec`."""

    def __init__(self, codec: PxFrameCodec) -> None:
        """Hold the codec every encode and decode call in this instance uses."""
        self._codec = codec

    # PC-112: encodes one BODY frame carrying the source's buckets and the caller's derived links
    def encode_body(self, sequence_id: UUID, frame: SequenceFrameInput, prev: int, next_id: int) -> EncodedFrame:
        """Encode one BODY frame: the input's buckets, under the given sequence id and derived links."""
        offset_microseconds = frame.source_time_offset // _MICROSECOND
        header = PxBodyHeader(sequence_id, frame.frame_id, prev, next_id, offset_microseconds)
        encoded = self._codec.encode(header, frame.buckets)
        return EncodedFrame(frame.frame_id, PxFrameType.BODY, encoded.frame, encoded.frame_hash)

    # PC-112: encodes the sealing END frame, which carries no buckets
    def encode_end(self, sequence_id: UUID, frame_id: int, prev: int) -> EncodedFrame:
        """Encode the sealing END frame, the last BODY id plus one, carrying no buckets."""
        header = PxEndHeader(sequence_id, frame_id, prev)
        encoded = self._codec.encode(header, ())
        return EncodedFrame(frame_id, PxFrameType.END, encoded.frame, encoded.frame_hash)

    # PC-112: reads the HEAD frame id open answers; anything else is refused, naming the type or reason met
    def decode_head_frame_id(self, head_frame: bytes) -> int:
        """Decode a HEAD frame and read its id; raise `ValueError` naming the type or reason met otherwise."""
        result = self._codec.decode(head_frame)
        match result:
            case PxFrameAccepted(frame=frame) if isinstance(frame.header, PxHeadHeader):
                return frame.header.frame_id
            case PxFrameAccepted(frame=frame):
                raise ValueError(f"{frame.header.frame_type.name} is not a HEAD frame")
            case _:
                raise ValueError(f"{result.reason.value} is not a HEAD frame")
