namespace Xio.Parallax.Client.Slots.Models;

/// <summary>
/// Options for <see cref="ParallaxClient.LookupBatchAsync"/>: how long to wait between progress
/// polls, how long to keep polling, and which look-up slot to resume.
/// </summary>
/// <param name="PollInterval">
/// How long to wait before the first progress poll, and the starting point for the bounded
/// exponential backoff between later polls. Required: there is no default.
/// </param>
/// <param name="PollTimeout">
/// How long to keep polling before giving up. Required: there is no default, since only the
/// caller knows how long is reasonable to wait.
/// </param>
public sealed record LookupBatchOptions(TimeSpan PollInterval,
                                         TimeSpan PollTimeout)
{
    /// <summary>An already-open look-up slot to resume instead of opening a new one.</summary>
    public string? ExistingLookupSlotId { get; init; }
}

/// <summary>
/// The outcome of a look-up slot batch: the slot it ran in, its final results, and its final
/// progress.
/// </summary>
/// <param name="LookupSlotId">The look-up slot the batch ran in.</param>
/// <param name="Results">The slot's results once no entry was left in the "retry" state.</param>
/// <param name="FinalProgress">The slot's progress once no entry was left in the "retry" state.</param>
public sealed record LookupBatchResult(string LookupSlotId,
                                        LookupResultsResponse Results,
                                        SlotProgressResponse FinalProgress);
