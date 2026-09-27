namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-102: BODY/END round trip through the real Common encoder and decoder; HEAD id decode and refusal
// PC-117: rework - an encode-time refusal from Common names the frame it refused
public sealed class SequenceFrameEncoderTests : IDisposable
{
    private readonly SequenceFrameEncoder _encoder = new();
    // PC-102: the reference provider comes from the shared Common composition
    private readonly ServiceProvider _referenceProvider = CommonServiceProviderFactory.Build();

    private IXioPxFrameEncoder ReferenceEncoder => _referenceProvider.GetRequiredService<IXioPxFrameEncoder>();

    private IXioPxFrameDecoder ReferenceDecoder => _referenceProvider.GetRequiredService<IXioPxFrameDecoder>();

    [Fact]
    public async Task A_body_frame_round_trips_through_the_real_common_encoder_and_decoder()
    {
        var sequenceId = Guid.NewGuid();
        var imageBytes = new byte[] { 1, 2, 3, 4, 5 };
        var frame = SequenceFrameInput.ForImage(7, TimeSpan.FromMilliseconds(250), imageBytes);

        var encoded = await _encoder.EncodeBodyAsync(sequenceId, frame, prev: 6, next: 8, CancellationToken.None);

        Assert.Equal(7, encoded.FrameId);
        Assert.Equal(PxFrameType.Body, encoded.FrameType);
        Assert.Equal(encoded.FrameHash.ToArray(), encoded.Bytes.ToArray()[^encoded.FrameHash.Length..]);

        var decoded = await ReferenceDecoder.DecodeAsync(new XioReadPxFrameRequest(encoded.Bytes), CancellationToken.None);
        var accepted = Assert.IsType<PxFrameAccepted<PxFrame>>(decoded);
        var header = Assert.IsType<PxBodyHeader>(accepted.Value.Header);
        Assert.Equal(sequenceId, header.SequenceId);
        Assert.Equal(7, header.FrameId);
        Assert.Equal(6, header.Prev);
        Assert.Equal(8, header.Next);
        Assert.Equal(250_000, header.SourceTimeOffsetMicroseconds);

        var bucket = Assert.Single(accepted.Value.Buckets);
        Assert.Equal(PxFrameConstants.ImageBucketTag, bucket.Entry.Tag);
        Assert.Equal(imageBytes, bucket.Data.ToArray());
    }

    [Fact]
    public async Task An_end_frame_round_trips_through_the_real_common_encoder_and_decoder()
    {
        var sequenceId = Guid.NewGuid();

        var encoded = await _encoder.EncodeEndAsync(sequenceId, frameId: 9, prev: 8, CancellationToken.None);

        Assert.Equal(9, encoded.FrameId);
        Assert.Equal(PxFrameType.End, encoded.FrameType);

        var decoded = await ReferenceDecoder.DecodeAsync(new XioReadPxFrameRequest(encoded.Bytes), CancellationToken.None);
        var accepted = Assert.IsType<PxFrameAccepted<PxFrame>>(decoded);
        var header = Assert.IsType<PxEndHeader>(accepted.Value.Header);
        Assert.Equal(sequenceId, header.SequenceId);
        Assert.Equal(9, header.FrameId);
        Assert.Equal(8, header.Prev);
        Assert.Empty(accepted.Value.Buckets);
    }

    // PC-117: a frame that reaches Common malformed despite SequenceFrameInput's own validation
    // (built by reflection, since the public constructor now refuses it) is named by frame id
    [Fact]
    public async Task EncodeBodyAsync_names_the_frame_when_common_itself_refuses_it()
    {
        var frame = UnvalidatedFrameWithEmptyBucketData(5);

        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => _encoder.EncodeBodyAsync(Guid.NewGuid(), frame, prev: 4, next: 6, CancellationToken.None));

        Assert.StartsWith("frame 5: ", exception.Message);
    }

    // PC-117: bypasses SequenceFrameInput's own validation, past its public constructor, to reach
    // the encoder with a frame Common itself still refuses, proving the encoder's own naming
    private static SequenceFrameInput UnvalidatedFrameWithEmptyBucketData(long frameId)
    {
        var frame = SequenceFrameInput.ForImage(frameId, TimeSpan.Zero, new byte[] { 1 });
        var field = typeof(SequenceFrameInput).GetField($"<{nameof(SequenceFrameInput.Buckets)}>k__BackingField", BindingFlags.Instance | BindingFlags.NonPublic);
        field!.SetValue(frame, new[] { new PxBucketContent(new PxBucketTag("TEST"), ReadOnlyMemory<byte>.Empty) });
        return frame;
    }

    [Fact]
    public async Task DecodeHeadFrameIdAsync_reads_the_id_of_a_head_the_encoder_made()
    {
        var sequenceId = Guid.NewGuid();
        var headResponse = await ReferenceEncoder.EncodeAsync(
            new XioEncodePxFrameRequest(new PxHeadHeader(sequenceId, 0), Array.Empty<PxBucketContent>()),
            CancellationToken.None);
        var headFrameBase64 = Convert.ToBase64String(headResponse.Frame.ToArray());

        var headFrameId = await _encoder.DecodeHeadFrameIdAsync(headFrameBase64, CancellationToken.None);

        Assert.Equal(0, headFrameId);
    }

    [Fact]
    public async Task DecodeHeadFrameIdAsync_refuses_a_body_by_name()
    {
        var frame = SequenceFrameInput.ForImage(1, TimeSpan.Zero, new byte[] { 9 });
        var encoded = await _encoder.EncodeBodyAsync(Guid.NewGuid(), frame, prev: 0, next: 2, CancellationToken.None);
        var bodyBase64 = Convert.ToBase64String(encoded.Bytes.ToArray());

        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => _encoder.DecodeHeadFrameIdAsync(bodyBase64, CancellationToken.None));

        Assert.Contains(nameof(PxFrameType.Body), exception.Message);
    }

    public void Dispose()
    {
        _encoder.Dispose();
        _referenceProvider.Dispose();
    }
}
