"""The sequence conversation's two verdict-carrying refusals: not committable, and still incomplete.

Mirrors `Xio.Parallax.Client.Sequences.Models.SequenceVerdictException` and
`SequenceCommitException`. Neither message ever names a ticket.
"""

# PC-111: sequence conversation errors

from __future__ import annotations

from typing import TYPE_CHECKING

from .wire import FRAME_STATE_NOT_PUBLISHED

if TYPE_CHECKING:
    from ..generated.models.sequence_commit_response import SequenceCommitResponse
    from ..generated.models.sequence_verdict_response import SequenceVerdictResponse


class SequenceVerdictError(Exception):
    """Raised when a sealed sequence's verdict is not committable: not connected, gaps, or errata.

    Nothing is committed; the sequence stays sealed for the caller to abandon or resolve through
    take-down. The message names the gap count, the errata count and whether the sequence is
    connected; it never names a ticket.
    """

    def __init__(self, verdict: SequenceVerdictResponse) -> None:
        """Create a new `SequenceVerdictError` carrying the refused verdict."""
        gap_count = len(verdict.gaps)
        errata_count = len(verdict.errata)
        super().__init__(
            f"the sequence is not committable: {gap_count} gap(s), {errata_count} errata, "
            f"connected = {verdict.connected}"
        )
        self.verdict = verdict


class SequenceCommitError(Exception):
    """Raised when a sequence's commit is still `incomplete` after every attempt was allowed.

    The message names how many frames were published and how many were not; it never names a
    ticket. Calling commit again later resumes from the first unpublished frame.
    """

    def __init__(self, commit: SequenceCommitResponse) -> None:
        """Create a new `SequenceCommitError` carrying the last incomplete commit."""
        frames = commit.frames
        unpublished = sum(1 for frame in frames if frame.state == FRAME_STATE_NOT_PUBLISHED)
        published = len(frames) - unpublished
        super().__init__(f"the sequence commit is still incomplete: {published} frame(s) published, {unpublished} unpublished")
        self.commit = commit
