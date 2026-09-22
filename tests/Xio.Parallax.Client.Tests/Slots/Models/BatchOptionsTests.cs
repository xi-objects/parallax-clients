namespace Xio.Parallax.Client.Tests.Slots.Models;

/// <summary>A present-but-blank slot id is a refusal at construction, never a request to <c>/slots//uploads/missing</c>.</summary>
public sealed class BatchOptionsTests
{
    [Fact]
    public void A_blank_existing_slot_id_is_refused()
    {
        var options = new RegisterBatchOptions(TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10));

        Assert.Null(options.ExistingSlotId);
        Assert.Throws<ArgumentException>(() => options with { ExistingSlotId = string.Empty });
        Assert.Throws<ArgumentException>(() => options with { ExistingSlotId = "   " });
        Assert.Equal("sl_x", (options with { ExistingSlotId = "sl_x" }).ExistingSlotId);
    }

    [Fact]
    public void A_blank_existing_lookup_slot_id_is_refused()
    {
        var options = new LookupBatchOptions(TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10));

        Assert.Null(options.ExistingLookupSlotId);
        Assert.Throws<ArgumentException>(() => options with { ExistingLookupSlotId = string.Empty });
        Assert.Equal("sl_y", (options with { ExistingLookupSlotId = "sl_y" }).ExistingLookupSlotId);
    }
}
