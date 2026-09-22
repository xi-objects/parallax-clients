namespace Xio.Parallax.Client;

/// <summary>
/// The record-polling call on <see cref="ParallaxClient"/>: waits for a registered image's
/// published record to reach a terminal outcome.
/// </summary>
public sealed partial class ParallaxClient
{
    /// <summary>
    /// Polls <see cref="GetRecordAsync"/> for the given hash until its outcome is terminal
    /// (<see cref="PublishedRecordOutcome.Published"/>, <see cref="PublishedRecordOutcome.TakenDown"/>
    /// or <see cref="PublishedRecordOutcome.Refused"/>). A record is published to the record
    /// store some seconds after registration, so <see cref="PublishedRecordOutcome.NoRecordAnswered"/>
    /// right after registering, and <see cref="PublishedRecordOutcome.Retry"/> while the store
    /// cannot yet answer, are both waited out with bounded exponential backoff starting from
    /// <see cref="RecordWaitOptions.PollInterval"/>, the same shape the slot conversations poll
    /// progress with.
    /// </summary>
    /// <param name="originalImageHash">The SHA-256 hash, lowercase hex, that keys the record.</param>
    /// <param name="options">How long to wait between polls, and how long to keep polling.</param>
    /// <param name="cancellationToken">Cancels the wait.</param>
    /// <returns>The published record, once its outcome is terminal.</returns>
    /// <exception cref="ParallaxClientException">
    /// <see cref="RecordWaitOptions.PollTimeout"/> elapsed while the outcome was still
    /// <see cref="PublishedRecordOutcome.NoRecordAnswered"/> or <see cref="PublishedRecordOutcome.Retry"/>.
    /// </exception>
    public async Task<PublishedRecordResponse> WaitForRecordAsync(
        string originalImageHash,
        RecordWaitOptions options,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrEmpty(originalImageHash);
        ArgumentNullException.ThrowIfNull(options);
        return await PollUntilTerminalAsync(
            () => GetRecordAsync(originalImageHash, cancellationToken),
            static record => IsTerminalOutcome(record.Outcome),
            options.PollInterval,
            options.PollTimeout,
            latest => $"Waiting for the published record for '{originalImageHash}' timed out after " +
                      $"{options.PollTimeout} with the last outcome '{DescribeOutcome(latest.Outcome)}'.",
            cancellationToken).ConfigureAwait(false);
    }

    private static bool IsTerminalOutcome(PublishedRecordOutcome? outcome)
        => outcome is PublishedRecordOutcome.Published or PublishedRecordOutcome.TakenDown or PublishedRecordOutcome.Refused;

    private static string DescribeOutcome(PublishedRecordOutcome? outcome)
        => outcome?.ToString() ?? "none";

    /// <summary>
    /// Polls the given call to a terminal result, using bounded exponential backoff from
    /// <paramref name="pollInterval"/>, doubling after every non-terminal poll up to
    /// <paramref name="pollTimeout"/>. Throws a <see cref="ParallaxClientException"/> built from
    /// the last poll once <paramref name="pollTimeout"/> elapses; never loops forever, and honors
    /// <paramref name="cancellationToken"/> on every wait.
    /// </summary>
    private static async Task<T> PollUntilTerminalAsync<T>(
        Func<Task<T>> poll,
        Func<T, bool> isTerminal,
        TimeSpan pollInterval,
        TimeSpan pollTimeout,
        Func<T, string> timeoutMessage,
        CancellationToken cancellationToken)
    {
        if (pollInterval <= TimeSpan.Zero)
        {
            throw new ArgumentOutOfRangeException(nameof(pollInterval), pollInterval, "Poll interval must be positive.");
        }

        if (pollTimeout <= TimeSpan.Zero)
        {
            throw new ArgumentOutOfRangeException(nameof(pollTimeout), pollTimeout, "Poll timeout must be positive.");
        }

        var stopwatch = Stopwatch.StartNew();
        var delay = pollInterval;
        while (true)
        {
            var latest = await poll().ConfigureAwait(false);
            if (isTerminal(latest))
            {
                return latest;
            }

            if (stopwatch.Elapsed >= pollTimeout)
            {
                throw new ParallaxClientException(timeoutMessage(latest));
            }

            var remaining = pollTimeout - stopwatch.Elapsed;
            var wait = delay < remaining ? delay : remaining;
            await Task.Delay(wait, cancellationToken).ConfigureAwait(false);
            var doubled = delay.Ticks <= long.MaxValue / 2 ? TimeSpan.FromTicks(delay.Ticks * 2) : TimeSpan.MaxValue;
            delay = doubled < pollTimeout ? doubled : pollTimeout;
        }
    }
}
