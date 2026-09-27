namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-102: SequenceHandle.ToString redacts the ticket
/// <summary>The ticket never reaches <see cref="SequenceHandle.ToString"/>, the same way an account token never reaches <see cref="ParallaxClientOptions"/>'s.</summary>
public sealed class SequenceHandleTests
{
    [Fact]
    public void ToString_OmitsTheTicket_ButKeepsTheSequenceId()
    {
        var sequenceId = Guid.NewGuid();
        var handle = new SequenceHandle(sequenceId, "distinctive-ticket-4f2a");

        var text = handle.ToString();

        Assert.DoesNotContain("distinctive-ticket-4f2a", text);
        Assert.Contains(sequenceId.ToString(), text);
    }
}
