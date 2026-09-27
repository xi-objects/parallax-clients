namespace Xio.Parallax.Client.Sequences.Models;

// PC-102: a sealed sequence the client refuses to commit: not connected, or gaps remain
/// <summary>
/// Thrown when a sequence's verdict, once sealed, is not committable: it is not connected, or it
/// still names gaps. Its message names the gap count, the errata count and whether the sequence
/// is connected; it never names a ticket.
/// </summary>
public sealed class SequenceVerdictException : Exception
{
    /// <summary>Creates a new <see cref="SequenceVerdictException"/> carrying the refused verdict.</summary>
    /// <param name="verdict">The verdict the sequence was sealed on, not committable.</param>
    public SequenceVerdictException(SequenceVerdictResponse verdict)
        : base(BuildMessage(verdict))
    {
        Verdict = verdict;
    }

    /// <summary>The verdict the sequence was sealed on, not committable.</summary>
    public SequenceVerdictResponse Verdict { get; }

    private static string BuildMessage(SequenceVerdictResponse verdict)
    {
        ArgumentNullException.ThrowIfNull(verdict);
        var gapCount = verdict.Gaps?.Count ?? 0;
        var errataCount = verdict.Errata?.Count ?? 0;
        var connected = verdict.Connected ?? false;
        return $"the sequence is not committable: {gapCount} gap(s), {errataCount} errata, connected = {connected}.";
    }
}
