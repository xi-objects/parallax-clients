namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-102: SequenceChainLinker derives prev/next with one frame of lookahead and refuses non-monotone ids
public sealed class SequenceChainLinkerTests
{
    [Fact]
    public async Task Three_frames_link_prev_and_next_with_the_end_id_after_the_last()
    {
        var frames = Frames(1, 2, 3);

        var links = await CollectAsync(frames, headFrameId: 0);

        Assert.Equal(
            new[] { (1L, 0L, 2L), (2L, 1L, 3L), (3L, 2L, 4L) },
            links.Select(link => (link.Frame.FrameId, link.Prev, link.Next)));
    }

    [Fact]
    public async Task Frames_with_room_between_ids_link_the_same_way()
    {
        var frames = Frames(10, 20, 30);

        var links = await CollectAsync(frames, headFrameId: 0);

        Assert.Equal(
            new[] { (10L, 0L, 20L), (20L, 10L, 30L), (30L, 20L, 31L) },
            links.Select(link => (link.Frame.FrameId, link.Prev, link.Next)));
    }

    // PC-102: the lookahead is checked before the frame ahead of it is yielded, so no link is yielded at all
    [Fact]
    public async Task A_non_monotone_id_is_refused_naming_both_ids_before_any_link_is_yielded()
    {
        var frames = Frames(5, 3);
        var links = new List<(SequenceFrameInput Frame, long Prev, long Next)>();

        var exception = await Assert.ThrowsAsync<ArgumentException>(async () =>
        {
            await foreach (var link in SequenceChainLinker.LinkAsync(frames.ReadFramesAsync(CancellationToken.None), headFrameId: 0))
            {
                links.Add(link);
            }
        });

        Assert.Contains("3", exception.Message);
        Assert.Contains("5", exception.Message);
        Assert.Empty(links);
    }

    [Fact]
    public async Task An_empty_source_yields_nothing()
    {
        var frames = Frames();

        var links = await CollectAsync(frames, headFrameId: 0);

        Assert.Empty(links);
    }

    private static FakeSequenceFrameSource Frames(params long[] frameIds)
    {
        return new FakeSequenceFrameSource(frameIds
            .Select(frameId => SequenceFrameInput.ForImage(frameId, TimeSpan.Zero, new byte[] { 1 }))
            .ToArray());
    }

    private static async Task<List<(SequenceFrameInput Frame, long Prev, long Next)>> CollectAsync(FakeSequenceFrameSource source, long headFrameId)
    {
        var links = new List<(SequenceFrameInput Frame, long Prev, long Next)>();
        await foreach (var link in SequenceChainLinker.LinkAsync(source.ReadFramesAsync(CancellationToken.None), headFrameId))
        {
            links.Add(link);
        }

        return links;
    }
}
