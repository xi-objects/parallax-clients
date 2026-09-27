namespace Xio.Parallax.Client.Sequences.Services;

// PC-102: composes Xio.Parallax.Common once, for the PX frames a sequence conversation sends and reads
/// <summary>
/// Encodes BODY and END sequence frames, and reads a HEAD frame's id, through one
/// <c>Xio.Parallax.Common</c> service provider, built lazily on first use and disposed with the
/// client that owns it. Nothing about the PX frame format is reimplemented here.
/// </summary>
internal sealed class SequenceFrameEncoder : IDisposable
{
    private readonly Lazy<ServiceProvider> _provider = new(BuildProvider);

    private IXioPxFrameEncoder Encoder => _provider.Value.GetRequiredService<IXioPxFrameEncoder>();

    private IXioPxFrameDecoder Decoder => _provider.Value.GetRequiredService<IXioPxFrameDecoder>();

    // PC-102: encodes one BODY frame carrying the source's buckets and the caller's derived links
    /// <summary>Encodes one BODY frame: the input's buckets, under the given sequence id and links.</summary>
    /// <param name="sequenceId">The sequence the frame belongs to.</param>
    /// <param name="frame">The frame to encode, as the source gave it.</param>
    /// <param name="prev">The frame's derived prev link.</param>
    /// <param name="next">The frame's derived next link.</param>
    /// <param name="cancellationToken">Cancels the encode.</param>
    /// <returns>The encoded BODY frame.</returns>
    public async Task<EncodedFrame> EncodeBodyAsync(Guid sequenceId, SequenceFrameInput frame, long prev, long next, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(frame);
        var offsetMicroseconds = frame.SourceTimeOffset.Ticks / TimeSpan.TicksPerMicrosecond;
        var header = new PxBodyHeader(sequenceId, frame.FrameId, prev, next, offsetMicroseconds);
        var response = await Encoder.EncodeAsync(new XioEncodePxFrameRequest(header, frame.Buckets), cancellationToken).ConfigureAwait(false);
        return new EncodedFrame(frame.FrameId, PxFrameType.Body, response.Frame, response.FrameHash);
    }

    // PC-102: encodes the sealing END frame, which carries no buckets
    /// <summary>Encodes the sealing END frame, the last BODY id plus one, carrying no buckets.</summary>
    /// <param name="sequenceId">The sequence the frame belongs to.</param>
    /// <param name="frameId">The END frame's id, the last BODY id plus one.</param>
    /// <param name="prev">The END frame's prev link, the last BODY id.</param>
    /// <param name="cancellationToken">Cancels the encode.</param>
    /// <returns>The encoded END frame.</returns>
    public async Task<EncodedFrame> EncodeEndAsync(Guid sequenceId, long frameId, long prev, CancellationToken cancellationToken)
    {
        var header = new PxEndHeader(sequenceId, frameId, prev);
        var response = await Encoder.EncodeAsync(new XioEncodePxFrameRequest(header, Array.Empty<PxBucketContent>()), cancellationToken).ConfigureAwait(false);
        return new EncodedFrame(frameId, PxFrameType.End, response.Frame, response.FrameHash);
    }

    // PC-102: reads the HEAD frame id open answers; anything else is refused, naming the type met
    /// <summary>Decodes open's base64 HEAD frame and reads its id, refusing anything but a HEAD frame.</summary>
    /// <param name="headFrameBase64">The base64 HEAD frame open answered.</param>
    /// <param name="cancellationToken">Cancels the decode.</param>
    /// <returns>The HEAD frame's id.</returns>
    public async Task<long> DecodeHeadFrameIdAsync(string headFrameBase64, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrEmpty(headFrameBase64);
        var bytes = Convert.FromBase64String(headFrameBase64);
        var read = await Decoder.DecodeAsync(new XioReadPxFrameRequest(bytes), cancellationToken).ConfigureAwait(false);
        return read switch
        {
            PxFrameAccepted<PxFrame> { Value.Header: PxHeadHeader head } => head.FrameId,
            PxFrameAccepted<PxFrame> accepted => throw new InvalidOperationException($"{accepted.Value.Header.FrameType} is not a HEAD frame."),
            PxFrameRefused<PxFrame> refused => throw new InvalidOperationException($"{refused.Reason} is not a HEAD frame."),
            _ => throw new InvalidOperationException("an unrecognized decode result is not a HEAD frame."),
        };
    }

    // PC-102: disposes the provider only if this encoder ever built one
    /// <summary>Disposes the Common service provider, only if this encoder ever built one.</summary>
    public void Dispose()
    {
        if (_provider.IsValueCreated)
        {
            _provider.Value.Dispose();
        }
    }

    private static ServiceProvider BuildProvider()
    {
        var services = new ServiceCollection();

        // PC-102: Common's hash service asks for ILogger<T>; no host is composing one here
        services.AddSingleton(typeof(ILogger<>), typeof(NullLogger<>));
        services.AddXioParallaxCommon();
        return services.BuildServiceProvider();
    }
}
