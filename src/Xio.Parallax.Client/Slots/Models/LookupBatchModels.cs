namespace Xio.Parallax.Client.Slots.Models;

/// <summary>
/// Options for <see cref="ParallaxClient.LookupBatchAsync"/>: which look-up slot to resume. A
/// look-up commit is terminal and answers its results directly, so there is nothing to poll for
/// and no timing to configure here.
/// </summary>
public sealed record LookupBatchOptions
{
    /// <summary>An already-open look-up slot to resume instead of opening a new one.</summary>
    public string? ExistingLookupSlotId
    {
        get;
        init => field = value is not null && string.IsNullOrWhiteSpace(value)
            ? throw new ArgumentException($"ExistingLookupSlotId is blank; omit it to open a new look-up slot.", nameof(value))
            : value;
    }
}

/// <summary>
/// The outcome of a look-up slot batch: the slot it ran in, the results its commit answered, and
/// its progress read once after that commit. A query can still land in the "retry" state here:
/// commit is terminal, so a "retry" query was never re-sent and never will be on this slot.
/// </summary>
/// <param name="LookupSlotId">The look-up slot the batch ran in.</param>
/// <param name="Results">The slot's results, as the commit answered them.</param>
/// <param name="FinalProgress">The slot's progress, read once right after commit.</param>
public sealed record LookupBatchResult(string LookupSlotId,
                                        LookupResultsResponse Results,
                                        SlotProgressResponse FinalProgress);
