namespace Xio.Parallax.Client.Sequences.Services;

// PC-102: derives prev/next links from a source's frames, one frame of lookahead
/// <summary>
/// Derives the prev and next links a source's frames carry no opinion about: the first frame's
/// prev is the sequence's HEAD id, each frame's next is the following frame's id, and the last
/// frame's next is therefore the END id (the last frame's id plus one). Buffers exactly one
/// frame of lookahead to learn each next before yielding.
/// </summary>
internal static class SequenceChainLinker
{
    // PC-102: yields (frame, prev, next) in source order, refusing a non-monotone id before yielding the frame ahead of it
    /// <summary>
    /// Reads <paramref name="frames"/> and yields each one with its derived prev and next link.
    /// A frame whose id is not above the frame read immediately before it (or, for the first
    /// frame, not above <paramref name="headFrameId"/>) is refused with an
    /// <see cref="ArgumentException"/> naming both ids, before the frame ahead of it is yielded,
    /// so no link ever names the offending id. An empty source yields nothing.
    /// </summary>
    /// <param name="frames">The source's frames, in chain order.</param>
    /// <param name="headFrameId">The sequence's HEAD id, the first frame's prev.</param>
    /// <param name="cancellationToken">Cancels the read.</param>
    /// <returns>Each frame with its derived prev and next link.</returns>
    public static async IAsyncEnumerable<(SequenceFrameInput Frame, long Prev, long Next)> LinkAsync(
        IAsyncEnumerable<SequenceFrameInput> frames,
        long headFrameId,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(frames);
        await using var enumerator = frames.GetAsyncEnumerator(cancellationToken);
        if (!await enumerator.MoveNextAsync().ConfigureAwait(false))
        {
            yield break;
        }

        var previousId = headFrameId;
        var current = enumerator.Current;
        RefuseUnlessAbove(current.FrameId, previousId);
        while (await enumerator.MoveNextAsync().ConfigureAwait(false))
        {
            var next = enumerator.Current;
            RefuseUnlessAbove(next.FrameId, current.FrameId);
            yield return (current, previousId, next.FrameId);
            previousId = current.FrameId;
            current = next;
        }

        yield return (current, previousId, current.FrameId + 1);
    }

    private static void RefuseUnlessAbove(long frameId, long previousId)
    {
        if (frameId <= previousId)
        {
            throw new ArgumentException($"frame id {frameId} is not above {previousId}.", nameof(frameId));
        }
    }
}
