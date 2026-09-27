namespace Xio.Parallax.Client.Sequences.Models;

// PC-102: one frame a source hands the client; the client derives its links, never the source
// PC-117: rework - one explicit constructor so every bad field is checked and named together,
// rather than the positional record's per-property initializers each throwing on the first offence
/// <summary>
/// One frame read from an <see cref="Interfaces.ISequenceFrameSource"/>: its id, its position
/// within the source's own media, and the buckets it carries. The source owns <see cref="FrameId"/>
/// but says nothing about prev or next; the client derives both from neighboring frames.
/// </summary>
public sealed record SequenceFrameInput
{
    /// <summary>The frame's id, monotone along the chain.</summary>
    public long FrameId { get; }

    /// <summary>The frame's position within its own media.</summary>
    public TimeSpan SourceTimeOffset { get; }

    /// <summary>The frame's buckets, in table order.</summary>
    public IReadOnlyList<PxBucketContent> Buckets { get; }

    // PC-117: refuses a non-positive id, a negative offset, no bucket, a repeated or malformed
    // bucket tag, or empty bucket data, naming every one together in one refusal
    /// <summary>Builds a frame input, validated above zero, non-negative, non-empty and well-formed.</summary>
    /// <param name="frameId">The frame's id, monotone along the chain.</param>
    /// <param name="sourceTimeOffset">The frame's position within its own media.</param>
    /// <param name="buckets">The frame's buckets, in table order.</param>
    public SequenceFrameInput(long frameId, TimeSpan sourceTimeOffset, IReadOnlyList<PxBucketContent> buckets)
    {
        ArgumentNullException.ThrowIfNull(buckets);
        var errors = ValidateAll(frameId, sourceTimeOffset, buckets);
        if (errors.Count > 0)
        {
            throw new ArgumentException(string.Join("; ", errors) + ".");
        }

        FrameId = frameId;
        SourceTimeOffset = sourceTimeOffset;
        Buckets = buckets;
    }

    // PC-102: one image frame, the bytes under the format's declared image bucket tag
    /// <summary>Builds a frame carrying a single image bucket, under <see cref="PxFrameConstants.ImageBucketTag"/>.</summary>
    /// <param name="frameId">The frame's id, monotone along the chain.</param>
    /// <param name="sourceTimeOffset">The frame's position within its own media.</param>
    /// <param name="imageBytes">The image's raw bytes.</param>
    /// <returns>A frame carrying the image under the image bucket tag.</returns>
    public static SequenceFrameInput ForImage(long frameId, TimeSpan sourceTimeOffset, ReadOnlyMemory<byte> imageBytes)
    {
        return new SequenceFrameInput(frameId, sourceTimeOffset, new[] { new PxBucketContent(PxFrameConstants.ImageBucketTag, imageBytes) });
    }

    // PC-117: refuses every bad field together instead of stopping at the first one
    private static List<string> ValidateAll(long frameId, TimeSpan sourceTimeOffset, IReadOnlyList<PxBucketContent> buckets)
    {
        var errors = new List<string>();
        if (frameId <= 0)
        {
            errors.Add($"a frame id must be above zero; was {frameId}");
        }

        if (sourceTimeOffset < TimeSpan.Zero)
        {
            errors.Add($"a source time offset must not be negative; was {sourceTimeOffset}");
        }

        if (buckets.Count == 0)
        {
            errors.Add("a frame needs at least one bucket");
            return errors;
        }

        var seen = new HashSet<PxBucketTag>();
        var duplicates = new List<PxBucketTag>();
        foreach (var bucket in buckets)
        {
            if (!IsWellFormedTag(bucket.Tag))
            {
                errors.Add($"bucket tag '{bucket.Tag.Value}' must be exactly {PxFrameConstants.BucketTagLength} bytes in "
                    + $"0x{PxFrameConstants.MinBucketTagByte:X2}-0x{PxFrameConstants.MaxBucketTagByte:X2}");
            }

            if (!seen.Add(bucket.Tag) && !duplicates.Contains(bucket.Tag))
            {
                duplicates.Add(bucket.Tag);
            }

            if (bucket.Data.IsEmpty)
            {
                errors.Add($"bucket '{bucket.Tag.Value}' has no data");
            }
        }

        foreach (var tag in duplicates)
        {
            errors.Add($"a frame's buckets repeat tag '{tag.Value}'");
        }

        return errors;
    }

    // PC-117: the shape itself, over Common's own PxFrameConstants, never a re-declared copy
    private static bool IsWellFormedTag(PxBucketTag tag)
    {
        var value = tag.Value;
        return value.Length == PxFrameConstants.BucketTagLength
            && value.All(character => character >= PxFrameConstants.MinBucketTagByte && character <= PxFrameConstants.MaxBucketTagByte);
    }
}

// PC-102: one PX frame ready to upload, its type and its already-encoded bytes
/// <summary>One PX sequence frame, already encoded: its id, its type, its bytes and its frame hash.</summary>
/// <param name="FrameId">The frame's id.</param>
/// <param name="FrameType">The frame's type: BODY or END, for a sequence frame.</param>
/// <param name="Bytes">The frame's encoded bytes, ready to upload.</param>
/// <param name="FrameHash">The frame's hash, the trailer <see cref="Bytes"/> ends with.</param>
public sealed record EncodedFrame(long FrameId,
                                  PxFrameType FrameType,
                                  ReadOnlyMemory<byte> Bytes,
                                  ReadOnlyMemory<byte> FrameHash);
