namespace Xio.Parallax.Client;

// PC-103: reads a sequence's gaps and progress, and amends its advisory expected size
/// <summary>The sequence progress routes on <see cref="ParallaxClient"/>: gaps, progress, expected size.</summary>
public sealed partial class ParallaxClient
{
    // PC-103: GET gaps through the generated builder, under the ticket header
    /// <summary>Answers one minted GAP frame per range the sequence's current chain carries.</summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>The sequence's current gaps.</returns>
    public async Task<SequenceGapsResponse> GetSequenceGapsAsync(SequenceHandle handle, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        return await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].Gaps.GetAsync(SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    // PC-103: GET progress through the generated builder, under the ticket header
    /// <summary>
    /// Reads the sequence's progress. Its state is one of open, sealed, committed, abandoned.
    /// </summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>The sequence's current verdict.</returns>
    public async Task<SequenceVerdictResponse> GetSequenceProgressAsync(SequenceHandle handle, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        return await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].Progress.GetAsync(SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    // PC-103: PUT expected-size through the generated builder, under the ticket header
    /// <summary>
    /// Amends the sequence's advisory expected size. A 409 means the sequence is no longer open.
    /// </summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="expectedSize">The sequence's new expected final frame count; must be above zero and fit an int32.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    public async Task AmendSequenceExpectedSizeAsync(SequenceHandle handle, long expectedSize, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        if (expectedSize is <= 0 or > int.MaxValue)
        {
            throw new ArgumentOutOfRangeException(nameof(expectedSize), expectedSize, "expectedSize must be between 1 and int.MaxValue.");
        }

        var body = new SequenceAmendExpectedSizeRequest { ExpectedSize = (int)expectedSize };
        await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].ExpectedSize
                .PutAsync(body, SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }
}
