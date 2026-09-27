"""The async mirror of `sequences.conversation`: the one-call sequence conversation.

See `conversation.py` for the shared shape; this module differs by `async def`/`await` throughout,
and by accepting either a `SequenceFrameSource` or an `AsyncSequenceFrameSource` (an async source is
preferred when a given object satisfies both).
"""

# PC-114: the sequence conversation's one-call register, async

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..frames.protocol import PxGapRange
from ..frames.source import AsyncSequenceFrameSource, SequenceFrameSource
from ..problems import ParallaxClientError
from .async_routes import AsyncSequenceRoutes
from .encoding import SequenceFrameEncoder
from .errors import SequenceCommitError, SequenceVerdictError
from .linker import link_frames, link_frames_async
from .models import (
    OpenedSequence,
    SequenceBatching,
    SequenceRegisterOptions,
    SequenceRegisterResult,
    VerdictCallback,
)
from .planning import FrameBatchPlanner, is_committable, is_selected_for_resume
from .wire import OUTCOME_INCOMPLETE, STATE_COMMITTED, STATE_OPEN, STATE_SEALED

if TYPE_CHECKING:
    from ..generated.models.sequence_commit_response import SequenceCommitResponse
    from ..generated.models.sequence_gaps_response import SequenceGapsResponse
    from ..generated.models.sequence_verdict_response import SequenceVerdictResponse

#: A frame id predicate: `True` when a frame the linker yields is one this seal actually uploads.
_Selects = Callable[[int], bool]

#: Either flavour of frame source `register_sequence` accepts; an async one is preferred when both.
AnySequenceFrameSource = SequenceFrameSource | AsyncSequenceFrameSource


# PC-114: the last BODY id and the END id the linker derived after reading the whole source
@dataclass(frozen=True, slots=True)
class _SourceTail:
    """The chain's last BODY id and the END id the linker derived after it, for a fresh seal."""

    last_body_id: int
    end_frame_id: int


def _refuse_unless_exactly_one_of_open_and_existing(options: SequenceRegisterOptions) -> None:
    """Raise `ValueError` naming `open` and `existing` unless exactly one of them is set."""
    if (options.open is None) == (options.existing is None):
        raise ValueError("exactly one of open and existing must be set")


def _select_every_frame(frame_id: int) -> bool:
    """A fresh open selects every frame the linker yields; only a resume filters."""
    return True


def _gap_ranges(response: SequenceGapsResponse) -> tuple[PxGapRange, ...]:
    """The gaps a `SequenceGapsResponse` carries, as `PxGapRange`s with 64-bit fields as `int`."""
    return tuple(PxGapRange(int(gap.from_), int(gap.to)) for gap in response.gaps)


class AsyncSequenceConversation(AsyncSequenceRoutes):
    """Mixin adding `register_sequence` to `AsyncParallaxClient`; async mirror of `SequenceConversation`."""

    # PC-114: opens or resumes, then carries the sequence through to its results
    async def register_sequence(
        self,
        source: AnySequenceFrameSource,
        options: SequenceRegisterOptions,
        on_verdict: VerdictCallback | None = None,
    ) -> SequenceRegisterResult:
        """Async mirror of `SequenceConversation.register_sequence`.

        `source` may be a `SequenceFrameSource` or an `AsyncSequenceFrameSource`; an async source is
        read through `read_frames_async` when the given object satisfies both.
        """
        _refuse_unless_exactly_one_of_open_and_existing(options)

        if options.open is not None:
            opened = await self.open_sequence(options.open)
            verdict = await self._seal_sequence(opened, source, options.batching, _select_every_frame, on_verdict)
            return await self._commit_verdict(opened, verdict, options)

        return await self._resume_sequence(options.existing, source, options, on_verdict)

    # PC-114: branches a resume on the sequence's own state, as its progress answers it
    async def _resume_sequence(
        self,
        existing: OpenedSequence,
        source: AnySequenceFrameSource,
        options: SequenceRegisterOptions,
        on_verdict: VerdictCallback | None,
    ) -> SequenceRegisterResult:
        """Async mirror of `SequenceConversation._resume_sequence`."""
        current = await self.get_sequence_progress(existing.handle)
        if on_verdict is not None:
            on_verdict(current)

        if current.state == STATE_OPEN:
            return await self._resume_open_sequence(existing, current, source, options, on_verdict)

        if current.state == STATE_SEALED:
            return await self._resume_sealed_sequence(existing, source, options, on_verdict)

        if current.state == STATE_COMMITTED:
            return await self._commit_and_read_results(existing, current, options)

        raise ParallaxClientError(f"a sequence in state {current.state!r} cannot be resumed")

    # PC-114: an open sequence gets only the frames above its reach or inside a gap, then END
    async def _resume_open_sequence(
        self,
        existing: OpenedSequence,
        current: SequenceVerdictResponse,
        source: AnySequenceFrameSource,
        options: SequenceRegisterOptions,
        on_verdict: VerdictCallback | None,
    ) -> SequenceRegisterResult:
        """Async mirror of `SequenceConversation._resume_open_sequence`."""
        if current.reach is None:
            raise ParallaxClientError("the Parallax API answered an open sequence's progress without its reach")
        reach = int(current.reach)
        gaps = _gap_ranges(await self.get_sequence_gaps(existing.handle))

        def selects(frame_id: int) -> bool:
            return is_selected_for_resume(frame_id, reach, gaps)

        verdict = await self._seal_sequence(existing, source, options.batching, selects, on_verdict)
        return await self._commit_verdict(existing, verdict, options)

    # PC-114: a sealed sequence gets only its gap fills, and no END
    async def _resume_sealed_sequence(
        self,
        existing: OpenedSequence,
        source: AnySequenceFrameSource,
        options: SequenceRegisterOptions,
        on_verdict: VerdictCallback | None,
    ) -> SequenceRegisterResult:
        """Async mirror of `SequenceConversation._resume_sealed_sequence`."""
        gaps = _gap_ranges(await self.get_sequence_gaps(existing.handle))

        def selects(frame_id: int) -> bool:
            return any(gap.range_from <= frame_id <= gap.range_to for gap in gaps)

        await self._upload_source_frames(existing, source, options.batching, selects)
        verdict = await self.get_sequence_progress(existing.handle)
        if on_verdict is not None:
            on_verdict(verdict)
        return await self._commit_verdict(existing, verdict, options)

    # PC-114: uploads the selected frames, then END as its own batch, and takes the verdict it answered
    async def _seal_sequence(
        self,
        sequence: OpenedSequence,
        source: AnySequenceFrameSource,
        batching: SequenceBatching,
        selects: _Selects,
        on_verdict: VerdictCallback | None,
    ) -> SequenceVerdictResponse:
        """Async mirror of `SequenceConversation._seal_sequence`."""
        tail = await self._upload_source_frames(sequence, source, batching, selects)
        if tail is None:
            raise ParallaxClientError(
                "a sequence needs at least one BODY; the source yielded no frame, and the sequence is left open"
            )

        encoder = SequenceFrameEncoder(self.frame_codec)
        end = encoder.encode_end(sequence.handle.sequence_id, tail.end_frame_id, tail.last_body_id)
        sealing = await self.upload_sequence_frames(sequence.handle, [end])
        if sealing.verdict is None:
            raise ParallaxClientError(
                f"the Parallax API admitted END frame {end.frame_id} without a verdict; the sequence did not seal"
            )
        if on_verdict is not None:
            on_verdict(sealing.verdict)
        return sealing.verdict

    # PC-114: streams the source through the linker, encodes and uploads the selected frames one batch at a time
    async def _upload_source_frames(
        self,
        sequence: OpenedSequence,
        source: AnySequenceFrameSource,
        batching: SequenceBatching,
        selects: _Selects,
    ) -> _SourceTail | None:
        """Read the whole source, an async source preferred when `source` satisfies both protocols;
        see `SequenceConversation._upload_source_frames`."""
        encoder = SequenceFrameEncoder(self.frame_codec)
        planner = FrameBatchPlanner(batching.max_request_bytes, batching.max_frames_per_request)
        tail: _SourceTail | None = None

        if isinstance(source, AsyncSequenceFrameSource):
            linked_frames = link_frames_async(source.read_frames_async(), sequence.head_frame_id)
            async for linked in linked_frames:
                tail = _SourceTail(linked.frame.frame_id, linked.next)
                if selects(linked.frame.frame_id):
                    encoded = encoder.encode_body(sequence.handle.sequence_id, linked.frame, linked.prev, linked.next)
                    batch = planner.add(encoded)
                    if batch is not None:
                        await self.upload_sequence_frames(sequence.handle, batch)
        else:
            for linked in link_frames(source.read_frames(), sequence.head_frame_id):
                tail = _SourceTail(linked.frame.frame_id, linked.next)
                if selects(linked.frame.frame_id):
                    encoded = encoder.encode_body(sequence.handle.sequence_id, linked.frame, linked.prev, linked.next)
                    batch = planner.add(encoded)
                    if batch is not None:
                        await self.upload_sequence_frames(sequence.handle, batch)

        remaining = planner.flush()
        if remaining is not None:
            await self.upload_sequence_frames(sequence.handle, remaining)
        return tail

    # PC-114: refuses a verdict that is not connected or still names a gap or an errata frame, then commits
    async def _commit_verdict(
        self, sequence: OpenedSequence, verdict: SequenceVerdictResponse, options: SequenceRegisterOptions
    ) -> SequenceRegisterResult:
        """Async mirror of `SequenceConversation._commit_verdict`."""
        if not is_committable(verdict.connected, len(verdict.gaps), len(verdict.errata)):
            raise SequenceVerdictError(verdict)
        return await self._commit_and_read_results(sequence, verdict, options)

    # PC-114: commits, retrying after the poll interval while incomplete and attempts remain, then reads results
    async def _commit_and_read_results(
        self, sequence: OpenedSequence, verdict: SequenceVerdictResponse, options: SequenceRegisterOptions
    ) -> SequenceRegisterResult:
        """Async mirror of `SequenceConversation._commit_and_read_results`."""
        commit: SequenceCommitResponse = await self.commit_sequence(sequence.handle)
        attempt = 1
        while commit.outcome == OUTCOME_INCOMPLETE:
            if attempt >= options.commit_attempts:
                raise SequenceCommitError(commit)
            await asyncio.sleep(options.poll_interval)
            commit = await self.commit_sequence(sequence.handle)
            attempt += 1

        results = await self.get_sequence_results(sequence.handle)
        return SequenceRegisterResult(sequence, verdict, commit, results)
