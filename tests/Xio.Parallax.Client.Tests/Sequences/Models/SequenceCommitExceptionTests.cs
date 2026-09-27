namespace Xio.Parallax.Client.Tests.Sequences.Models;

// PC-104: SequenceCommitException's message counts published and unpublished frames and carries the commit
public sealed class SequenceCommitExceptionTests
{
    [Fact]
    public void The_message_counts_published_and_unpublished_frames()
    {
        var commit = new SequenceCommitResponse
        {
            Outcome = "incomplete",
            Frames =
            [
                new SequenceCommitFrameResponse { FrameId = 1, State = "published" },
                new SequenceCommitFrameResponse { FrameId = 2, State = "alreadyPublished" },
                new SequenceCommitFrameResponse { FrameId = 3, State = "notPublished" },
            ],
        };

        var exception = new SequenceCommitException(commit);

        Assert.Contains("2 frame(s) published", exception.Message, StringComparison.Ordinal);
        Assert.Contains("1 unpublished", exception.Message, StringComparison.Ordinal);
        Assert.Same(commit, exception.Commit);
    }
}
