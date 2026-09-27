namespace Xio.Parallax.Client.Sequences.Models;

// PC-104: a commit still incomplete after every attempt the caller allowed
/// <summary>
/// Thrown when a sequence's commit is still <c>incomplete</c> after every attempt
/// <see cref="SequenceRegisterOptions.CommitAttempts"/> allowed. Its message names how many frames
/// were published and how many were not; it never names a ticket. Calling commit again later
/// resumes from the first unpublished frame.
/// </summary>
public sealed class SequenceCommitException : Exception
{
    // PC-104: carries the last commit response, which answered incomplete
    /// <summary>Creates a new <see cref="SequenceCommitException"/> carrying the last incomplete commit.</summary>
    /// <param name="commit">The last commit response, whose outcome was incomplete.</param>
    public SequenceCommitException(SequenceCommitResponse commit)
        : base(BuildMessage(commit))
    {
        Commit = commit;
    }

    // PC-104: the last commit response, incomplete
    /// <summary>The last commit response, whose outcome was incomplete.</summary>
    public SequenceCommitResponse Commit { get; }

    private static string BuildMessage(SequenceCommitResponse commit)
    {
        ArgumentNullException.ThrowIfNull(commit);
        var frames = commit.Frames ?? [];
        var unpublished = frames.Count(frame => string.Equals(frame.State, SequenceWire.NotPublished, StringComparison.Ordinal));
        return $"the sequence commit is still incomplete: {frames.Count - unpublished} frame(s) published, {unpublished} unpublished.";
    }
}
