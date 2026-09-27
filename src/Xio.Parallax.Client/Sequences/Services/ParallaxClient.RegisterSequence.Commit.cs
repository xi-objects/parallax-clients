namespace Xio.Parallax.Client;

// PC-104: the closing phase of the register conversation: refuse a verdict that cannot commit,
// commit with retries on incomplete, then read the results
/// <summary>The verdict check, commit and results phases of <see cref="ParallaxClient.RegisterSequenceAsync"/>.</summary>
public sealed partial class ParallaxClient
{
    // PC-104: refuses a verdict that is not connected or still names a gap, then commits
    private async Task<SequenceRegisterResult> CommitVerdictAsync(
        OpenedSequence sequence,
        SequenceVerdictResponse verdict,
        SequenceRegisterOptions options,
        CancellationToken cancellationToken)
    {
        if (verdict.Connected != true || verdict.Gaps is { Count: > 0 })
        {
            throw new SequenceVerdictException(verdict);
        }

        return await CommitAndReadResultsAsync(sequence, verdict, options, cancellationToken).ConfigureAwait(false);
    }

    // PC-104: commits, calling again after the poll interval while incomplete and attempts remain, then reads results
    private async Task<SequenceRegisterResult> CommitAndReadResultsAsync(
        OpenedSequence sequence,
        SequenceVerdictResponse verdict,
        SequenceRegisterOptions options,
        CancellationToken cancellationToken)
    {
        var commit = await CommitSequenceAsync(sequence.Handle, cancellationToken).ConfigureAwait(false);
        for (var attempt = 1; string.Equals(commit.Outcome, SequenceWire.Incomplete, StringComparison.Ordinal); attempt++)
        {
            if (attempt >= options.CommitAttempts)
            {
                throw new SequenceCommitException(commit);
            }

            await Task.Delay(options.PollInterval, cancellationToken).ConfigureAwait(false);
            commit = await CommitSequenceAsync(sequence.Handle, cancellationToken).ConfigureAwait(false);
        }

        var results = await GetSequenceResultsAsync(sequence.Handle, cancellationToken).ConfigureAwait(false);
        return new SequenceRegisterResult(sequence, verdict, commit, results, verdict.Errata ?? []);
    }
}
