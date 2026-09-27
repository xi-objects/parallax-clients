namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-102: validates SequenceFrameInput's frame id, offset and bucket rules, and ForImage
public sealed class SequenceFrameInputTests
{
    private static readonly PxBucketContent OneBucket = new(new PxBucketTag("TEST"), new byte[] { 1 });

    [Fact]
    public void A_frame_id_must_be_above_zero()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(0, TimeSpan.Zero, new[] { OneBucket }));

        Assert.Equal("frameId", exception.ParamName);
    }

    [Fact]
    public void A_source_time_offset_must_not_be_negative()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.FromSeconds(-1), new[] { OneBucket }));

        Assert.Equal("sourceTimeOffset", exception.ParamName);
    }

    [Fact]
    public void At_least_one_bucket_is_required()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.Zero, Array.Empty<PxBucketContent>()));

        Assert.Equal("buckets", exception.ParamName);
    }

    [Fact]
    public void A_repeated_bucket_tag_is_refused()
    {
        var buckets = new[] { OneBucket, OneBucket };

        var exception = Assert.Throws<ArgumentException>(() => new SequenceFrameInput(1, TimeSpan.Zero, buckets));

        Assert.Equal("buckets", exception.ParamName);
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
