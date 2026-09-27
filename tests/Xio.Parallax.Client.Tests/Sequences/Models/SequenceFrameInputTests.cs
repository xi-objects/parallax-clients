namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-102: validates SequenceFrameInput's frame id, offset and bucket rules, and ForImage
// PC-117: rework - bad fields are refused together, naming each; bucket tag and data covered too
public sealed class SequenceFrameInputTests
{
    private static readonly PxBucketContent OneBucket = new(new PxBucketTag("TEST"), new byte[] { 1 });

    [Fact]
    public void A_frame_id_must_be_above_zero()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(0, TimeSpan.Zero, new[] { OneBucket }));

        Assert.Contains("a frame id must be above zero", exception.Message);
    }

    [Fact]
    public void A_source_time_offset_must_not_be_negative()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.FromSeconds(-1), new[] { OneBucket }));

        Assert.Contains("a source time offset must not be negative", exception.Message);
    }

    [Fact]
    public void At_least_one_bucket_is_required()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.Zero, Array.Empty<PxBucketContent>()));

        Assert.Contains("a frame needs at least one bucket", exception.Message);
    }

    [Fact]
    public void A_repeated_bucket_tag_is_refused()
    {
        var buckets = new[] { OneBucket, OneBucket };

        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.Zero, buckets));

        Assert.Contains("a frame's buckets repeat tag 'TEST'", exception.Message);
    }

    // PC-117: the bucket tag shape comes from Common's own rule, not a re-declared copy
    [Fact]
    public void A_malformed_bucket_tag_is_refused()
    {
        var buckets = new[] { new PxBucketContent(new PxBucketTag("AB"), new byte[] { 1 }) };

        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.Zero, buckets));

        Assert.Contains("bucket tag 'AB' must be exactly", exception.Message);
    }

    [Fact]
    public void Empty_bucket_data_is_refused()
    {
        var buckets = new[] { new PxBucketContent(new PxBucketTag("TEST"), ReadOnlyMemory<byte>.Empty) };

        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.Zero, buckets));

        Assert.Contains("bucket 'TEST' has no data", exception.Message);
    }

    // PC-117: every bad frame-input field is named together in one refusal
    [Fact]
    public void Every_bad_field_is_named_together_in_one_refusal()
    {
        var buckets = new[] { new PxBucketContent(new PxBucketTag("AB"), ReadOnlyMemory<byte>.Empty) };

        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(0, TimeSpan.FromSeconds(-1), buckets));

        Assert.Contains("a frame id must be above zero", exception.Message);
        Assert.Contains("a source time offset must not be negative", exception.Message);
        Assert.Contains("bucket tag 'AB' must be exactly", exception.Message);
        Assert.Contains("bucket 'AB' has no data", exception.Message);
    }

    [Fact]
    public void ForImage_puts_the_bytes_under_the_image_bucket_tag()
    {
        var imageBytes = new byte[] { 9, 8, 7 };

        var frame = SequenceFrameInput.ForImage(3, TimeSpan.FromSeconds(2), imageBytes);

        var bucket = Assert.Single(frame.Buckets);
        Assert.Equal(PxFrameConstants.ImageBucketTag, bucket.Tag);
        Assert.Equal(imageBytes, bucket.Data.ToArray());
        Assert.Equal(3, frame.FrameId);
        Assert.Equal(TimeSpan.FromSeconds(2), frame.SourceTimeOffset);
    }
}
