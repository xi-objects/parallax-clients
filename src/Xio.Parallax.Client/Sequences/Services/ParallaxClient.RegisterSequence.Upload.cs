namespace Xio.Parallax.Client;

// PC-104: the upload phase of the register conversation: the source's frames, linked, encoded and
// batched under the caller's caps, then the sealing END
/// <summary>The upload and seal phases of <see cref="ParallaxClient.RegisterSequenceAsync"/>.</summary>
public sealed partial class ParallaxClient
{
    // PC-104: uploads the selected frames, then END as its own batch, and takes the verdict the END batch answered
    private async Task<SequenceVerdictResponse> SealSequenceAsync(
        OpenedSequence sequence,
        ISequenceFrameSource source,
        SequenceBatching batching,
        Func<long, bool> selects,
        IProgress<SequenceVerdictResponse>? progress,
        CancellationToken cancellationToken)
    {
        var tail = await UploadSourceFramesAsync(sequence, source, batching, selects, cancellationToken).ConfigureAwait(false)
            ?? throw new InvalidOperationException("a sequence needs at least one BODY; the source yielded no frame, and the sequence is left open.");

        var sequenceId = sequence.Handle.SequenceId;
        var end = await _sequenceFrameEncoder.EncodeEndAsync(sequenceId, tail.EndFrameId, tail.LastBodyId, cancellationToken).ConfigureAwait(false);
        var sealing = await UploadSequenceFramesAsync(sequence.Handle, [end], cancellationToken).ConfigureAwait(false);
        var verdict = sealing.Verdict
            ?? throw new ParallaxClientException($"The Parallax API admitted END frame {end.FrameId} without a verdict; the sequence did not seal.");
        progress?.Report(verdict);
        return verdict;
    }

    // PC-104: streams the source through the linker, encodes and uploads the selected frames one batch at a time,
    // each batch bounded by its whole multipart body
    /// <summary>
    /// Reads the whole source through the chain linker from the sequence's HEAD id, encodes each
    /// frame <paramref name="selects"/> keeps as a BODY with its derived links, and uploads them in
    /// batches: a batch closes when the next frame would take it past either cap, the byte cap
    /// counting the whole multipart body the batch sends (every part's bytes, part headers,
    /// boundaries and the closing delimiter). A frame whose request alone would exceed
    /// <see cref="SequenceBatching.MaxRequestBytes"/> is refused before it, or any batch holding
    /// it, is sent; batches before it may already have gone. At most one batch plus the linker's
    /// one frame of lookahead is held at a time.
    /// </summary>
    /// <returns>The last BODY id and the END id the linker derived, or null when the source yielded no frame.</returns>
    private async Task<SequenceSourceTail?> UploadSourceFramesAsync(
        OpenedSequence sequence,
        ISequenceFrameSource source,
        SequenceBatching batching,
        Func<long, bool> selects,
        CancellationToken cancellationToken)
    {
        var sequenceId = sequence.Handle.SequenceId;
        var batch = new List<EncodedFrame>();
        var batchBytes = 0L;
        SequenceSourceTail? tail = null;
        var linked = SequenceChainLinker.LinkAsync(source.ReadFramesAsync(cancellationToken), sequence.HeadFrameId, cancellationToken);
        await foreach (var (frame, prev, next) in linked.ConfigureAwait(false))
        {
            tail = new SequenceSourceTail(frame.FrameId, next);
            if (!selects(frame.FrameId))
            {
                continue;
            }

            var encoded = await _sequenceFrameEncoder.EncodeBodyAsync(sequenceId, frame, prev, next, cancellationToken).ConfigureAwait(false);
            var alone = MultipartRequestContent.MeasureSequenceFrames([encoded]);
            if (alone > batching.MaxRequestBytes)
            {
                throw new ArgumentException(
                    $"frame {frame.FrameId} alone makes a {alone}-byte request, above MaxRequestBytes {batching.MaxRequestBytes}.",
                    nameof(source));
            }

            var appended = MultipartRequestContent.MeasureSequenceFrames([encoded, encoded]) - alone;
            if (batch.Count > 0 && (batch.Count + 1 > batching.MaxFramesPerRequest || batchBytes + appended > batching.MaxRequestBytes))
            {
                await UploadSequenceFramesAsync(sequence.Handle, batch, cancellationToken).ConfigureAwait(false);
                batch = new List<EncodedFrame>();
            }

            batchBytes = batch.Count == 0 ? alone : batchBytes + appended;
            batch.Add(encoded);
        }

        if (batch.Count > 0)
        {
            await UploadSequenceFramesAsync(sequence.Handle, batch, cancellationToken).ConfigureAwait(false);
        }

        return tail;
    }

    // PC-104: the chain's last BODY id and the END id the linker derived after it
    private sealed record SequenceSourceTail(long LastBodyId, long EndFrameId);
}
