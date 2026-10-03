namespace Xio.Parallax.Client.Verification.Services;

// PC-119: the version-1 layout, field by field; the frames go in through a digest so the signed bytes stay 115
// whatever the sequence's length. Refuses rather than lays out bytes nobody should sign, as Common's builder does
/// <summary>Builds the version-1 sequence summary preimage.</summary>
public sealed class SequenceSummaryPreimageBuilder : ISequenceSummaryPreimageBuilder
{
    /// <inheritdoc/>
    public byte[] Build(XioSequenceSummaryPreimageRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        RequireHash(request.SequenceHash.Span, nameof(request.SequenceHash));
        if (request.ExpectedSize < 0 || request.FinalSize < 0 || request.FramesReceived < 0)
        {
            throw new ArgumentException("A summary's sizes and counts are never negative.", nameof(request));
        }

        var digest = FramesDigest(request.Frames);
        var preimage = new byte[VerificationConstants.SummaryPreimageLength];
        var span = preimage.AsSpan();
        var offset = 0;
        span[offset++] = VerificationConstants.ImplementedSummaryPreimageVersion;
        BinaryPrimitives.WriteUInt16BigEndian(span[offset..], (ushort)VerificationConstants.SummaryPreimageTag.Length);
        offset += 2;
        Encoding.ASCII.GetBytes(VerificationConstants.SummaryPreimageTag, span[offset..]);
        offset += VerificationConstants.SummaryPreimageTag.Length;
        BinaryPrimitives.WriteUInt16BigEndian(span[offset..], VerificationConstants.Blake3HashLength);
        offset += 2;
        request.SequenceHash.Span.CopyTo(span[offset..]);
        offset += VerificationConstants.Blake3HashLength;
        span[offset++] = request.ExpectedSize is null ? (byte)0 : (byte)1;
        BinaryPrimitives.WriteInt32BigEndian(span[offset..], request.ExpectedSize ?? 0);
        offset += 4;
        BinaryPrimitives.WriteInt32BigEndian(span[offset..], request.FinalSize);
        offset += 4;
        span[offset++] = request.Connected ? (byte)1 : (byte)0;
        span[offset++] = request.Sealed ? (byte)1 : (byte)0;
        BinaryPrimitives.WriteInt64BigEndian(span[offset..], request.Reach);
        offset += 8;
        BinaryPrimitives.WriteInt32BigEndian(span[offset..], request.FramesReceived);
        offset += 4;
        BinaryPrimitives.WriteUInt32BigEndian(span[offset..], (uint)request.Frames.Count);
        offset += 4;
        digest.CopyTo(span[offset..]);
        Debug.Assert(offset + VerificationConstants.Blake3HashLength == VerificationConstants.SummaryPreimageLength);
        return preimage;
    }

    /// <inheritdoc/>
    public byte[] FramesDigest(IReadOnlyList<SequenceSummaryFrameEntry> frames)
    {
        ArgumentNullException.ThrowIfNull(frames);
        if (frames.Count == 0)
        {
            throw new ArgumentException("A summary with no frames has no preimage: a committed sequence carries at least one BODY.", nameof(frames));
        }

        var entries = new byte[frames.Count * SummaryFrameEntryLength];
        var span = entries.AsSpan();
        for (var index = 0; index < frames.Count; index++)
        {
            var frame = frames[index] ?? throw new ArgumentException($"Frame {index} is absent.", nameof(frames));
            RequireHash(frame.OriginalImageHash.Span, nameof(frame.OriginalImageHash));
            RequireHash(frame.FrameHash.Span, nameof(frame.FrameHash));
            var entry = span.Slice(index * SummaryFrameEntryLength, SummaryFrameEntryLength);
            BinaryPrimitives.WriteInt64BigEndian(entry, frame.FrameId);
            frame.OriginalImageHash.Span.CopyTo(entry[8..]);
            frame.FrameHash.Span.CopyTo(entry[(8 + VerificationConstants.Blake3HashLength)..]);
        }

        return Blake3Hasher
            .Hash(entries)
            .AsSpan()
            .ToArray();
    }

    // PC-119: an i64 frame id, then two 32-byte hashes
    private const int SummaryFrameEntryLength = 8 + (2 * VerificationConstants.Blake3HashLength);

    private static void RequireHash(ReadOnlySpan<byte> hash, string name)
    {
        if (hash.Length != VerificationConstants.Blake3HashLength)
        {
            throw new ArgumentException($"{name} is {hash.Length} bytes; every hash in a summary is {VerificationConstants.Blake3HashLength}.", name);
        }
    }
}
