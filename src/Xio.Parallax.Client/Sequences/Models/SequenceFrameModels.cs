namespace Xio.Parallax.Client.Sequences.Models;

// PC-102: one frame a source hands the client; the client derives its links, never the source
/// <summary>
/// One frame read from an <see cref="Interfaces.ISequenceFrameSource"/>: its id, its position
/// within the source's own media, and the buckets it carries. The source owns <see cref="FrameId"/>
/// but says nothing about prev or next; the client derives both from neighboring frames.
/// </summary>
/// <param name="FrameId">The frame's id, monotone along the chain; validated above zero.</param>
/// <param name="SourceTimeOffset">The frame's position within its own media; validated non-negative.</param>
/// <param name="Buckets">The frame's buckets, in table order; validated non-empty with no repeated tag.</param>
public sealed record SequenceFrameInput(long FrameId,
                                        TimeSpan SourceTimeOffset,
                                        IReadOnlyList<PxBucketContent> Buckets)
{
    /// <summary>The frame's id, monotone along the chain.</summary>
    public long FrameId { get; } = ValidateFrameId(FrameId);

    /// <summary>The frame's position within its own media.</summary>
    public TimeSpan SourceTimeOffset { get; } = ValidateSourceTimeOffset(SourceTimeOffset);

    /// <summary>The frame's buckets, in table order.</summary>
    public IReadOnlyList<PxBucketContent> Buckets { get; } = ValidateBuckets(Buckets);

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

    private static long ValidateFrameId(long frameId)
    {
        return frameId > 0
            ? frameId
            : throw new ArgumentException($"a frame id must be above zero; was {frameId}.", nameof(frameId));
    }

    private static TimeSpan ValidateSourceTimeOffset(TimeSpan sourceTimeOffset)
    {
        return sourceTimeOffset >= TimeSpan.Zero
            ? sourceTimeOffset
            : throw new ArgumentException($"a source time offset must not be negative; was {sourceTimeOffset}.", nameof(sourceTimeOffset));
    }

    private static IReadOnlyList<PxBucketContent> ValidateBuckets(IReadOnlyList<PxBucketContent> buckets)
    {
        ArgumentNullException.ThrowIfNull(buckets);
        if (buckets.Count == 0)
        {
            throw new ArgumentException("a frame needs at least one bucket.", nameof(buckets));
        }

        if (buckets.Select(bucket => bucket.Tag).Distinct().Count() != buckets.Count)
        {
            throw new ArgumentException("a frame's buckets repeat a tag.", nameof(buckets));
        }

        return buckets;
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
