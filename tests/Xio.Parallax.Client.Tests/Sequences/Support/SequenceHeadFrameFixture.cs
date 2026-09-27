namespace Xio.Parallax.Client.Tests.Sequences.Support;

// PC-103: a real HEAD frame, base64, standing in for what open's own response carries
/// <summary>Encodes a real HEAD frame through Common, the same way the server itself mints one.</summary>
internal static class SequenceHeadFrameFixture
{
    // PC-103: encodes through the shared Common provider
    /// <summary>Encodes a HEAD frame for the given sequence and frame id, and base64s it.</summary>
    /// <param name="sequenceId">The sequence the HEAD frame belongs to.</param>
    /// <param name="headFrameId">The HEAD frame's own id.</param>
    /// <returns>The HEAD frame, base64-encoded, as open's own response carries it.</returns>
    internal static async Task<string> EncodeBase64Async(Guid sequenceId, long headFrameId)
    {
        using var provider = CommonServiceProviderFactory.Build();
        var encoder = provider.GetRequiredService<IXioPxFrameEncoder>();
        var response = await encoder.EncodeAsync(
            new XioEncodePxFrameRequest(new PxHeadHeader(sequenceId, headFrameId), Array.Empty<PxBucketContent>()),
            CancellationToken.None);
        return Convert.ToBase64String(response.Frame.ToArray());
    }
}
