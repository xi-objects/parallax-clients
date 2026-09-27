namespace Xio.Parallax.Client.Sequences.Models;

// PC-102: the operator-configured upload caps a batched frame upload must respect; no default
/// <summary>
/// The operator-configured caps a batched sequence frame upload must respect. Neither cap is
/// declared by the OpenAPI document, so the caller states them; there is no default.
/// </summary>
/// <param name="MaxRequestBytes">The maximum total byte size of one multipart upload request.</param>
/// <param name="MaxFramesPerRequest">The maximum number of frames carried by one multipart upload request.</param>
public sealed record SequenceBatching(long MaxRequestBytes,
                                      int MaxFramesPerRequest)
{
    /// <summary>The maximum total byte size of one multipart upload request.</summary>
    public long MaxRequestBytes { get; } = MaxRequestBytes > 0
        ? MaxRequestBytes
        : throw new ArgumentException($"MaxRequestBytes must be above zero; was {MaxRequestBytes}.", nameof(MaxRequestBytes));

    /// <summary>The maximum number of frames carried by one multipart upload request.</summary>
    public int MaxFramesPerRequest { get; } = MaxFramesPerRequest > 0
        ? MaxFramesPerRequest
        : throw new ArgumentException($"MaxFramesPerRequest must be above zero; was {MaxFramesPerRequest}.", nameof(MaxFramesPerRequest));
}

// PC-102: how RegisterSequenceAsync (PC-104) opens or resumes, batches and retries a commit
/// <summary>
/// Options for the sequence register conversation: whether it opens a new sequence or resumes an
/// existing one, how it batches uploads, and how it waits for and retries an incomplete commit.
/// </summary>
/// <param name="PollInterval">How long to wait between commit retries. Required: there is no default.</param>
/// <param name="CommitAttempts">
/// How many times to call commit, including the first call, before giving up on an <c>incomplete</c>
/// outcome. Required: there is no default; at least one attempt is always made.
/// </param>
/// <param name="Batching">The operator-configured upload batching caps. Required: there is no default.</param>
public sealed record SequenceRegisterOptions(TimeSpan PollInterval,
                                             int CommitAttempts,
                                             SequenceBatching Batching)
{
    /// <summary>How long to wait between commit retries.</summary>
    public TimeSpan PollInterval { get; } = PollInterval > TimeSpan.Zero
        ? PollInterval
        : throw new ArgumentException($"PollInterval must be above zero; was {PollInterval}.", nameof(PollInterval));

    /// <summary>How many times to call commit before giving up on an <c>incomplete</c> outcome.</summary>
    public int CommitAttempts { get; } = CommitAttempts >= 1
        ? CommitAttempts
        : throw new ArgumentException($"CommitAttempts must be at least one; was {CommitAttempts}.", nameof(CommitAttempts));

    /// <summary>
    /// A new sequence to open, reading its frames from the start. Exactly one of <see cref="Open"/>
    /// and <see cref="Existing"/> is set; which one is validated once the conversation starts.
    /// </summary>
    public SequenceOpenRequest? Open { get; init; }

    // PC-104: the sequence a first run opened, its handle and HEAD id, rather than a bare handle
    /// <summary>
    /// A sequence a first run opened, as <c>OpenSequenceAsync</c> answered it, to resume. Exactly one
    /// of <see cref="Open"/> and <see cref="Existing"/> is set; which one is validated once the
    /// conversation starts.
    /// </summary>
    public OpenedSequence? Existing { get; init; }
}

// PC-104: the outcome of the register conversation, led by the opened sequence rather than a bare handle
/// <summary>
/// The outcome of registering a sequence: the sequence it ran in, the verdict the client sealed
/// it on, its commit and its final results, and the verdict's errata frames.
/// </summary>
/// <param name="Sequence">The sequence the conversation ran in: its handle and its HEAD id.</param>
/// <param name="Verdict">The verdict the sequence was sealed on.</param>
/// <param name="Commit">The sequence's commit response.</param>
/// <param name="Results">The sequence's final results.</param>
/// <param name="Errata">The verdict's errata frames: each frame id and the original image hash it matched.</param>
public sealed record SequenceRegisterResult(OpenedSequence Sequence,
                                            SequenceVerdictResponse Verdict,
                                            SequenceCommitResponse Commit,
                                            SequenceResultsResponse Results,
                                            IReadOnlyList<SequenceErrataFrameResponse> Errata);
