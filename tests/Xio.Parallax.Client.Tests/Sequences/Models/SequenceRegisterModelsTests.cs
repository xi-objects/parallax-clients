namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-102: validates SequenceBatching's required positive caps
public sealed class SequenceBatchingTests
{
    [Fact]
    public void MaxRequestBytes_must_be_above_zero()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceBatching(0, 1));

        Assert.Equal("MaxRequestBytes", exception.ParamName);
    }

    [Fact]
    public void MaxFramesPerRequest_must_be_above_zero()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceBatching(1024, 0));

        Assert.Equal("MaxFramesPerRequest", exception.ParamName);
    }

    [Fact]
    public void Positive_caps_are_kept()
    {
        var batching = new SequenceBatching(1024, 8);

        Assert.Equal(1024, batching.MaxRequestBytes);
        Assert.Equal(8, batching.MaxFramesPerRequest);
    }
}

// PC-102: validates SequenceRegisterOptions' required poll interval and commit attempts
public sealed class SequenceRegisterOptionsTests
{
    private static readonly SequenceBatching Batching = new(1024, 8);

    [Fact]
    public void PollInterval_must_be_above_zero()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceRegisterOptions(TimeSpan.Zero, 1, Batching));

        Assert.Equal("PollInterval", exception.ParamName);
    }

    [Fact]
    public void CommitAttempts_must_be_at_least_one()
    {
        var exception = Assert.Throws<ArgumentException>(() => new SequenceRegisterOptions(TimeSpan.FromSeconds(1), 0, Batching));

        Assert.Equal("CommitAttempts", exception.ParamName);
    }

    [Fact]
    public void Open_and_existing_are_both_left_null_by_default()
    {
        var options = new SequenceRegisterOptions(TimeSpan.FromSeconds(1), 3, Batching);

        Assert.Null(options.Open);
        Assert.Null(options.Existing);

        var resuming = options with { Existing = new SequenceHandle(Guid.NewGuid(), "t") };

        Assert.NotNull(resuming.Existing);
        Assert.Null(resuming.Open);
    }
}
