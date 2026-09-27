"""The sequence conversation's public surface: its models and its two verdict-carrying errors.

Mirrors `Xio.Parallax.Client.Sequences`. `wire.py`'s words are this package's own internal
vocabulary, not re-exported here, the way `SequenceWire` stays internal in .NET.
"""

# PC-111: the sequence conversation's public names, re-exported once

from .errors import SequenceCommitError, SequenceVerdictError
from .models import (
    EncodedFrame,
    OpenedSequence,
    SequenceBatching,
    SequenceHandle,
    SequenceOpenRequest,
    SequenceRegisterOptions,
    SequenceRegisterResult,
    VerdictCallback,
)

__all__ = [
    "EncodedFrame",
    "OpenedSequence",
    "SequenceBatching",
    "SequenceCommitError",
    "SequenceHandle",
    "SequenceOpenRequest",
    "SequenceRegisterOptions",
    "SequenceRegisterResult",
    "SequenceVerdictError",
    "VerdictCallback",
]
