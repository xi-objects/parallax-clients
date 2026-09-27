namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-102: SequenceVerdictException's message names gap count, errata count and connected
public sealed class SequenceVerdictExceptionTests
{
    [Fact]
    public void The_message_names_gap_count_errata_count_and_connected()
    {
        var verdict = new SequenceVerdictResponse
        {
            Connected = false,
            Gaps = [new SequenceGapRangeResponse { From = 2, To = 4 }],
            Errata = [new SequenceErrataFrameResponse { FrameId = 3 }],
        };

        var exception = new SequenceVerdictException(verdict);

        Assert.Contains("1 gap", exception.Message);
        Assert.Contains("1 errata", exception.Message);
        Assert.Contains("connected = False", exception.Message);
        Assert.Same(verdict, exception.Verdict);
    }

    [Fact]
    public void A_verdict_with_no_gaps_or_errata_counts_zero()
    {
        var verdict = new SequenceVerdictResponse { Connected = true };

        var exception = new SequenceVerdictException(verdict);

        Assert.Contains("0 gap", exception.Message);
        Assert.Contains("0 errata", exception.Message);
        Assert.Contains("connected = True", exception.Message);
    }
}
