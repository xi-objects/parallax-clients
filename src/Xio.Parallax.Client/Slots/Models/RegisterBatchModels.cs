namespace Xio.Parallax.Client.Slots.Models;

/// <summary>
/// Options for <see cref="ParallaxClient.RegisterBatchAsync"/>: how long to wait between progress
/// polls, how long to keep polling, and which slot to resume.
/// </summary>
/// <param name="PollInterval">
/// How long to wait before the first progress poll, and the starting point for the bounded
/// exponential backoff between later polls. Required: there is no default.
/// </param>
/// <param name="PollTimeout">
/// How long to keep polling before giving up. Required: there is no default, since only the
/// caller knows how long is reasonable to wait.
/// </param>
public sealed record RegisterBatchOptions(TimeSpan PollInterval,
                                           TimeSpan PollTimeout)
{
    /// <summary>
    /// An already-open slot to resume instead of opening a new one. Running the same batch call
    /// again over the same items, naming the slot it opened, is how a caller resumes after an
    /// interruption.
    /// </summary>
    public string? ExistingSlotId { get; init; }
}

/// <summary>
/// The outcome of a registration slot batch: the slot it ran in, its commit, its final progress,
/// and every upload outcome this run made.
/// </summary>
/// <param name="SlotId">The slot the batch ran in.</param>
/// <param name="Commit">The slot's commit response.</param>
/// <param name="FinalProgress">The slot's progress once no entry was left in the "retry" state.</param>
/// <param name="UploadOutcomes">Every per-image outcome from every upload call this run made.</param>
public sealed record RegisterBatchResult(string SlotId,
                                          SlotCommitResponse Commit,
                                          SlotProgressResponse FinalProgress,
                                          IReadOnlyList<SlotUploadOutcomeResponse> UploadOutcomes);

/// <summary>One image and its manifests to register as part of a slot batch.</summary>
/// <param name="Image">The image to upload.</param>
/// <param name="Manifests">The manifests that precede the image on the wire.</param>
public sealed record RegistrationItem(ImageUpload Image,
                                       IReadOnlyList<ManifestPart> Manifests);
