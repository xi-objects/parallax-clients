namespace Xio.Parallax.Client.Verification.Services;

// PC-119: what makes "this image is frame N of this sequence" provable. The sequence hash proves the ordered frame
// hashes; the summary signature proves which frame id and which image each one stands for, the sizes and the verdict
/// <summary>Checks a published sequence record: its sequence hash recomputed from the listed frame hashes, and its summary signature.</summary>
internal interface ISequenceSummaryChecker
{
    /// <summary>Returns the <c>sequenceHash</c> and <c>summarySignature</c> checks.</summary>
    /// <exception cref="VerificationRefusedException">The record states a summary preimage version other than 1.</exception>
    IReadOnlyList<VerificationCheck> Check(XioSequenceSummaryCheckRequest request);
}

/// <summary>The sequence record checks over the version-1 summary preimage.</summary>
internal sealed class SequenceSummaryChecker(IVerificationEncoding _encoding,
                                             ISequenceSummaryPreimageBuilder _preimageBuilder,
                                             ISignatureChecker _signatureChecker) : ISequenceSummaryChecker
{
    /// <inheritdoc/>
    public IReadOnlyList<VerificationCheck> Check(XioSequenceSummaryCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var sequence = request.Sequence;
        ArgumentNullException.ThrowIfNull(sequence, nameof(request.Sequence));
        RequireImplementedVersion(sequence.SummaryPreimageVersion);

        var frames = ReadFrames(sequence.Frames, out var framesProblem);
        return [CheckSequenceHash(frames, framesProblem, request.Admission.ContentHash), CheckSummarySignature(sequence, frames, framesProblem, request.Admission)];
    }

    // PC-119: a version this verifier does not lay out is refused, never guessed at - the same stance as a canonical version it does not know
    private static void RequireImplementedVersion(int? version)
    {
        if (version is { } stated && stated != VerificationConstants.ImplementedSummaryPreimageVersion)
        {
            throw new VerificationRefusedException(
                $"The record states summaryPreimageVersion {stated}; this verifier lays out version {VerificationConstants.ImplementedSummaryPreimageVersion} only.");
        }
    }

    private VerificationCheck CheckSequenceHash(List<SequenceSummaryFrameEntry>? frames, string? framesProblem, ReadOnlyMemory<byte> contentHash)
    {
        if (frames is null)
        {
            return new VerificationCheck(VerificationConstants.SequenceHashCheck, VerificationOutcome.Failed, framesProblem!);
        }

        var concatenated = new byte[frames.Count * VerificationConstants.Blake3HashLength];
        for (var index = 0; index < frames.Count; index++)
        {
            frames[index].FrameHash.Span.CopyTo(concatenated.AsSpan(index * VerificationConstants.Blake3HashLength));
        }

        var recomputed = Blake3Hasher.Hash(concatenated);
        return recomputed.AsSpan().SequenceEqual(contentHash.Span)
            ? new VerificationCheck(VerificationConstants.SequenceHashCheck, VerificationOutcome.Passed, "BLAKE3-256 over the listed frame hashes, in order, equals contentHash.")
            : new VerificationCheck(VerificationConstants.SequenceHashCheck, VerificationOutcome.Failed, $"BLAKE3-256 over the listed frame hashes is {recomputed}; the record's contentHash differs.");
    }

    private VerificationCheck CheckSummarySignature(PublishedSequence sequence,
                                                    List<SequenceSummaryFrameEntry>? frames,
                                                    string? framesProblem,
                                                    RecordAdmissionResult admission)
    {
        var hasVersion = sequence.SummaryPreimageVersion is not null;
        var hasSignature = !string.IsNullOrEmpty(sequence.SummarySignature);
        if (!hasVersion && !hasSignature)
        {
            return new VerificationCheck(VerificationConstants.SummarySignatureCheck, VerificationOutcome.NotPerformed,
                "The record declares no summary signature (a sequence committed before summary signing): each frame's id and image hash are reported, not proven.");
        }

        if (!hasVersion || !hasSignature)
        {
            return new VerificationCheck(VerificationConstants.SummarySignatureCheck, VerificationOutcome.Failed,
                "The record declares a summary signature without its preimage version, or a version without a signature.");
        }

        if (frames is null)
        {
            return new VerificationCheck(VerificationConstants.SummarySignatureCheck, VerificationOutcome.Failed, framesProblem!);
        }

        if (sequence.FinalSize is not { } finalSize || sequence.Verdict is not { } verdict
            || verdict.Connected is not { } connected || verdict.Sealed is not { } isSealed
            || verdict.Reach is not { } reach || verdict.FramesReceived is not { } framesReceived)
        {
            return new VerificationCheck(VerificationConstants.SummarySignatureCheck, VerificationOutcome.Failed,
                "The summary lacks its final size or a verdict field, so its preimage cannot be built.");
        }

        byte[] preimage;
        try
        {
            preimage = _preimageBuilder.Build(new XioSequenceSummaryPreimageRequest(
                admission.ContentHash, sequence.ExpectedSize, finalSize, connected, isSealed, reach, framesReceived, frames));
        }
        catch (ArgumentException ex)
        {
            return new VerificationCheck(VerificationConstants.SummarySignatureCheck, VerificationOutcome.Failed,
                $"The summary preimage cannot be built: {ex.Message}");
        }

        return _signatureChecker.Check(new XioSignatureCheckRequest(
            VerificationConstants.SummarySignatureCheck, admission.PublicKey, preimage, sequence.SummarySignature));
    }

    // PC-119: every listed frame decoded once, for both checks; the first one that cannot be read names itself
    private List<SequenceSummaryFrameEntry>? ReadFrames(List<PublishedSequenceFrame>? listed, out string? problem)
    {
        if (listed is null || listed.Count == 0)
        {
            problem = "The sequence lists no frames; a committed sequence carries at least one BODY.";
            return null;
        }

        var frames = new List<SequenceSummaryFrameEntry>(listed.Count);
        for (var index = 0; index < listed.Count; index++)
        {
            var frame = listed[index];
            var imageHash = _encoding.TryHex(frame?.OriginalImageHash);
            var frameHash = _encoding.TryHex(frame?.FrameHash);
            if (frame?.FrameId is not { } frameId
                || imageHash?.Length != VerificationConstants.Blake3HashLength
                || frameHash?.Length != VerificationConstants.Blake3HashLength)
            {
                problem = $"Listed frame {index} lacks a frame id, or its originalImageHash or frameHash is not a 32-byte hex hash.";
                return null;
            }

            frames.Add(new SequenceSummaryFrameEntry(frameId, imageHash, frameHash));
        }

        problem = null;
        return frames;
    }
}
