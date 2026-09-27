namespace Xio.Parallax.Client;

// PC-103: commits a sequence (the caller retries an incomplete outcome), reads its results, and
// abandons it outright
/// <summary>The sequence closing routes on <see cref="ParallaxClient"/>: commit, results, abandon.</summary>
public sealed partial class ParallaxClient
{
    // PC-103: POST commit through the generated builder, under the ticket header
    /// <summary>
    /// Commits the sequence. The outcome is one of registered, alreadyRegistered, incomplete;
    /// "incomplete" means the sequence record was not written this call, and the caller retries
    /// by calling commit again, which resumes from the first unpublished frame.
    /// </summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>The commit's outcome, and every frame's own commit state.</returns>
    public async Task<SequenceCommitResponse> CommitSequenceAsync(SequenceHandle handle, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        return await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].Commit.PostAsync(SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    // PC-103: GET results through the generated builder, under the ticket header
    /// <summary>Reads the sequence's final results. A 409 means the sequence is not committed yet.</summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>The sequence's outcome, final size and commit time.</returns>
    public async Task<SequenceResultsResponse> GetSequenceResultsAsync(SequenceHandle handle, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        return await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].Results.GetAsync(SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    // PC-103: DELETE the sequence through the generated builder, under the ticket header
    /// <summary>Abandons the sequence at once, purging its pool and closing its custody ledger.</summary>
    /// <param name="handle">The sequence's id and ticket.</param>
    /// <param name="cancellationToken">Cancels the call.</param>
    /// <returns>The sequence's id, its final state, and how many packets were purged.</returns>
    public async Task<SequenceAbandonResponse> AbandonSequenceAsync(SequenceHandle handle, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(handle);
        return await ExecuteAsync(
            () => Api.Sequences[handle.SequenceId.ToString()].DeleteAsync(SequenceTicketConfiguration(handle.Ticket), cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }
}
