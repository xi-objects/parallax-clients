namespace Xio.Parallax.Client;

// PC-103: uploads sequence frames and removes one BODY member, both under the sequence's ticket
/// <summary>The sequence frame conversation on <see cref="ParallaxClient"/>: upload, and remove one.</summary>
public sealed partial class ParallaxClient
{
    // PC-103: one octet-stream part per frame, under the ticket header, through the raw multipart sender
    /// <summary>
    /// Uploads one or more sequence frames as a single multipart batch: one
    /// application/octet-stream part per frame, its part name the frame's own id, in the order
    /// given. The response's verdict is present only when this batch sealed the sequence; a 409
    /// means the sequence's own state (already sealed, committed or abandoned) refuses the batch.
    /// </summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="frames">The encoded frames to upload, in order.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>Every frame's admission outcome, and the verdict when this batch sealed the sequence.</returns>
    public async Task<SequenceFrameBatchResponse> UploadSequenceFramesAsync(
        SequenceHandle handle,
        IReadOnlyList<EncodedFrame> frames,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        ArgumentNullException.ThrowIfNull(frames);
        if (frames.Count == 0)
        {
            throw new ArgumentException("uploading a sequence's frames needs at least one frame.", nameof(frames));
        }

        var content = MultipartRequestContent.CreateForSequenceFrames(frames);
        var pathParameters = SequencePathParameters(handle.SequenceId);
        return await ExecuteAsync(
            () => MultipartRequestSender.PostAsync(
                _requestAdapter,
                SequenceFramesUrlTemplate,
                pathParameters,
                content,
                SequenceFrameBatchResponse.CreateFromDiscriminatorValue,
                SequenceFramesErrorMapping,
                cancellationToken,
                SequenceTicketHeaders(handle.Ticket)),
            cancellationToken).ConfigureAwait(false);
    }

    // PC-103: removes one BODY frame through the generated builder, under the ticket header
    /// <summary>
    /// Removes one BODY member from the sequence. A 409 means the sequence is no longer open;
    /// this route only ever acts on an open sequence.
    /// </summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="frameId">The BODY frame's id to remove.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    public async Task RemoveSequenceFrameAsync(SequenceHandle handle, long frameId, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].Frames[frameId]
                .DeleteAsync(SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }
}
