namespace Xio.Parallax.Client;

/// <summary>
/// Shared machinery for the slot conversations: hashing, chunking uploads under the caller's
/// batching caps, and polling progress to a terminal state.
/// </summary>
public sealed partial class ParallaxClient
{
    private UploadBatching RequireBatching()
    {
        return _options.Batching ?? throw new ParallaxClientException(
            "Batching a slot conversation requires ParallaxClientOptions.Batching; the server's " +
            "request-byte and image-count caps are operator configuration that this client refuses to guess at.");
    }

    private static string Sha256Hex(ReadOnlyMemory<byte> bytes)
    {
        Span<byte> hash = stackalloc byte[32];
        SHA256.HashData(bytes.Span, hash);
        return Convert.ToHexStringLower(hash);
    }

    private static IEnumerable<IReadOnlyList<T>> ChunkByBatching<T>(
        IReadOnlyList<T> items,
        UploadBatching batching,
        Func<T, long> sizeOf)
    {
        var current = new List<T>();
        var currentSize = 0L;
        foreach (var item in items)
        {
            var size = sizeOf(item);
            var wouldExceedCount = current.Count + 1 > batching.MaxImagesPerRequest;
            var wouldExceedBytes = current.Count > 0 && currentSize + size > batching.MaxRequestBytes;
            if (current.Count > 0 && (wouldExceedCount || wouldExceedBytes))
            {
                yield return current;
                current = new List<T>();
                currentSize = 0;
            }

            current.Add(item);
            currentSize += size;
        }

        if (current.Count > 0)
        {
            yield return current;
        }
    }

    /// <summary>
    /// Polls the given progress endpoint, reporting every poll, until no entry is left in the
    /// "retry" state, using bounded exponential backoff from <paramref name="pollInterval"/>.
    /// Throws when <paramref name="pollTimeout"/> elapses first.
    /// </summary>
    private async Task<SlotProgressResponse> PollUntilNoRetryAsync(
        Func<Task<SlotProgressResponse?>> poll,
        string slotId,
        TimeSpan pollInterval,
        TimeSpan pollTimeout,
        IProgress<SlotProgressResponse>? progress,
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
            var latest = await ExecuteAsync(poll, cancellationToken).ConfigureAwait(false);
            progress?.Report(latest);
            if (!HasRetryEntries(latest))
            {
                return latest;
            }

            if (stopwatch.Elapsed >= pollTimeout)
            {
                throw new ParallaxClientException(
                    $"Polling slot '{slotId}' progress timed out after {pollTimeout} while entries were still in the 'retry' state.");
            }

            var remaining = pollTimeout - stopwatch.Elapsed;
            var wait = delay < remaining ? delay : remaining;
            await Task.Delay(wait, cancellationToken).ConfigureAwait(false);
            var doubled = delay.Ticks <= long.MaxValue / 2 ? TimeSpan.FromTicks(delay.Ticks * 2) : TimeSpan.MaxValue;
            delay = doubled < pollTimeout ? doubled : pollTimeout;
        }
    }

    private static bool HasRetryEntries(SlotProgressResponse progressResponse)
        => progressResponse.Entries?.Any(entry => string.Equals(entry.State, "retry", StringComparison.Ordinal)) ?? false;
}
