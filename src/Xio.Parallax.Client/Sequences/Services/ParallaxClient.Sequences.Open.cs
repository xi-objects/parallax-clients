namespace Xio.Parallax.Client;

// PC-103: opens a sequence; the account's sequences_enabled gate answers 403
/// <summary>Opens a sequence for the calling account, through the raw multipart sender.</summary>
public sealed partial class ParallaxClient
{
    // PC-103: the root path parameters come from RootPathParameters(), the one place they are built
    /// <summary>
    /// Opens a new sequence for the calling account: sends every manifest as a
    /// manifest[&lt;kind&gt;] part and, when given, <see cref="SequenceOpenRequest.ExpectedSize"/>
    /// as a text part. A 403 means the calling account's sequences feature is not enabled.
    /// </summary>
    /// <param name="request">The manifests, and optional expected size, to open with.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>The opened sequence's handle, and the id of the HEAD frame that opened it.</returns>
    public async Task<OpenedSequence> OpenSequenceAsync(SequenceOpenRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        var content = MultipartRequestContent.CreateForSequenceOpen(request.Manifests, request.ExpectedSize);
        var pathParameters = RootPathParameters();
        var response = await ExecuteAsync(
            () => MultipartRequestSender.PostAsync(
                _requestAdapter,
                SequenceOpenUrlTemplate,
                pathParameters,
                content,
                SequenceOpenResponse.CreateFromDiscriminatorValue,
                SequenceOpenErrorMapping,
                cancellationToken),
            cancellationToken).ConfigureAwait(false);

        var sequenceId = response.SequenceId
            ?? throw new ParallaxClientException("The Parallax API opened a sequence without naming its id.");
        var ticket = response.Ticket
            ?? throw new ParallaxClientException("The Parallax API opened a sequence without naming its ticket.");
        var headFrameBase64 = response.HeadFrame
            ?? throw new ParallaxClientException("The Parallax API opened a sequence without its HEAD frame.");
        var headFrameId = await _sequenceFrameEncoder.DecodeHeadFrameIdAsync(headFrameBase64, cancellationToken).ConfigureAwait(false);
        return new OpenedSequence(new SequenceHandle(sequenceId, ticket), headFrameId);
    }
}
