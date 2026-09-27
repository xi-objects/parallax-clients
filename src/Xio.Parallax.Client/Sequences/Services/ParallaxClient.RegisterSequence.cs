namespace Xio.Parallax.Client;

// PC-104: the sequence register conversation in one call: open or resume, upload, seal, commit, results
/// <summary>
/// The sequence register conversation on <see cref="ParallaxClient"/>: open (or resume) a
/// sequence, upload the source's frames in batches, seal it with END, commit it and read its results.
/// </summary>
public sealed partial class ParallaxClient
{
    // PC-104: opens or resumes, then carries the sequence through to its results; errata refuse before commit
    /// <summary>
    /// Registers a sequence of frames in one call: opens a sequence (or resumes the one
    /// <see cref="SequenceRegisterOptions.Existing"/> names), reads <paramref name="source"/>,
    /// encodes each frame as a BODY with its derived links, uploads them in batches under
    /// <see cref="SequenceRegisterOptions.Batching"/>, seals the sequence with END, commits it
    /// (retrying an incomplete commit) and reads its results. Running the call again over the same
    /// source with <see cref="SequenceRegisterOptions.Existing"/> resumes after an interruption:
    /// an open sequence gets only the frames inside a gap or above its reach, then END; a sealed one
    /// only its gap fills; a committed one only its commit again.
    /// </summary>
    /// <param name="source">The frames to register, in chain order.</param>
    /// <param name="options">Whether to open or resume, the batching caps, and the commit retry policy.</param>
    /// <param name="progress">Reported with every verdict the conversation reads.</param>
    /// <param name="cancellationToken">Cancels the whole conversation.</param>
    /// <returns>The sequence, the verdict it was sealed on, its commit and its results.</returns>
    /// <exception cref="SequenceVerdictException">
    /// The sealed sequence is not connected, still has gaps or names errata frames; nothing was committed, and the
    /// sequence stays sealed for the caller to abandon or to resolve through take-down.
    /// </exception>
    /// <exception cref="SequenceCommitException">The commit was still incomplete after every allowed attempt.</exception>
    public async Task<SequenceRegisterResult> RegisterSequenceAsync(
        ISequenceFrameSource source,
        SequenceRegisterOptions options,
        IProgress<SequenceVerdictResponse>? progress,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(options);
        if ((options.Open is null) == (options.Existing is null))
        {
            throw new ArgumentException(
                $"exactly one of {nameof(SequenceRegisterOptions.Open)} and {nameof(SequenceRegisterOptions.Existing)} must be set.",
                nameof(options));
        }

        if (options.Open is { } openRequest)
        {
            var opened = await OpenSequenceAsync(openRequest, cancellationToken).ConfigureAwait(false);
            var verdict = await SealSequenceAsync(opened, source, options.Batching, static _ => true, progress, cancellationToken).ConfigureAwait(false);
            return await CommitVerdictAsync(opened, verdict, options, cancellationToken).ConfigureAwait(false);
        }

        return await ResumeSequenceAsync(options.Existing!, source, options, progress, cancellationToken).ConfigureAwait(false);
    }

    // PC-104: branches a resume on the sequence's own state, as its progress answers it
    private async Task<SequenceRegisterResult> ResumeSequenceAsync(
        OpenedSequence existing,
        ISequenceFrameSource source,
        SequenceRegisterOptions options,
        IProgress<SequenceVerdictResponse>? progress,
        CancellationToken cancellationToken)
    {
        var current = await GetSequenceProgressAsync(existing.Handle, cancellationToken).ConfigureAwait(false);
        progress?.Report(current);
        switch (current.State)
        {
            case SequenceWire.Open:
                {
                    var reach = current.Reach
                        ?? throw new ParallaxClientException("The Parallax API answered an open sequence's progress without its reach.");
                    var gaps = await ReadGapRangesAsync(existing.Handle, cancellationToken).ConfigureAwait(false);
                    var verdict = await SealSequenceAsync(
                        existing,
                        source,
                        options.Batching,
                        frameId => frameId > reach || LiesInGap(frameId, gaps),
                        progress,
                        cancellationToken).ConfigureAwait(false);
                    return await CommitVerdictAsync(existing, verdict, options, cancellationToken).ConfigureAwait(false);
                }

            case SequenceWire.Sealed:
                {
                    var gaps = await ReadGapRangesAsync(existing.Handle, cancellationToken).ConfigureAwait(false);
                    await UploadSourceFramesAsync(existing, source, options.Batching, frameId => LiesInGap(frameId, gaps), cancellationToken).ConfigureAwait(false);
                    var verdict = await GetSequenceProgressAsync(existing.Handle, cancellationToken).ConfigureAwait(false);
                    progress?.Report(verdict);
                    return await CommitVerdictAsync(existing, verdict, options, cancellationToken).ConfigureAwait(false);
                }

            case SequenceWire.Committed:
                return await CommitAndReadResultsAsync(existing, current, options, cancellationToken).ConfigureAwait(false);

            default:
                throw new InvalidOperationException($"a sequence in state '{current.State}' cannot be resumed.");
        }
    }

    // PC-104: the sequence's current gap ranges, read from the gaps route
    private async Task<IReadOnlyList<SequenceGapResponse>> ReadGapRangesAsync(SequenceHandle handle, CancellationToken cancellationToken)
    {
        var response = await GetSequenceGapsAsync(handle, cancellationToken).ConfigureAwait(false);
        return response.Gaps ?? [];
    }

    // PC-104: whether a frame id lies inside any of the given inclusive gap ranges
    private static bool LiesInGap(long frameId, IReadOnlyList<SequenceGapResponse> gaps)
        => gaps.Any(gap => gap.From <= frameId && frameId <= gap.To);
}
