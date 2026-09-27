namespace Xio.Parallax.Client.Sequences.Models;

// PC-102: the sequence id and ticket every route past open carries; the ticket never prints
/// <summary>
/// A sequence's id and the ticket every route past open sends as <c>X-Sequence-Ticket</c>.
/// <see cref="ToString"/> prints <see cref="SequenceId"/> but redacts <see cref="Ticket"/>, the
/// same way <see cref="Shared.Models.ParallaxClientOptions"/> redacts its secrets.
/// </summary>
/// <param name="SequenceId">The sequence's id.</param>
/// <param name="Ticket">The sequence's ticket, sent as the <c>X-Sequence-Ticket</c> header.</param>
public sealed record SequenceHandle(Guid SequenceId,
                                    string Ticket)
{
    /// <summary>
    /// Prints <see cref="SequenceId"/> but redacts <see cref="Ticket"/>, so <see cref="ToString"/>
    /// (and the compiler-synthesised record equality diagnostics that call it) never surfaces it.
    /// </summary>
    /// <param name="builder">The builder the record's <see cref="ToString"/> writes into.</param>
    /// <returns>Always true, so the base member list is printed after these fields.</returns>
    private bool PrintMembers(StringBuilder builder)
    {
        builder.Append("SequenceId = ").Append(SequenceId);
        builder.Append(", Ticket = [redacted]");
        return true;
    }
}

// PC-102: a freshly opened sequence, its handle and the HEAD frame id decoded from open's response
/// <summary>A sequence just opened: its handle, and the id of the HEAD frame that opened it.</summary>
/// <param name="Handle">The sequence's id and ticket.</param>
/// <param name="HeadFrameId">The id of the HEAD frame open answered, decoded through Common.</param>
public sealed record OpenedSequence(SequenceHandle Handle,
                                    long HeadFrameId);
