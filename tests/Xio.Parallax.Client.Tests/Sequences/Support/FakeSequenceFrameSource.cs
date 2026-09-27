namespace Xio.Parallax.Client.Tests.Sequences.Support;

// PC-102: a fixed in-memory frame source, standing in for the ingestion this interface defers to
/// <summary>A fixed in-memory <see cref="ISequenceFrameSource"/>, streaming the frames it is given.</summary>
/// <param name="frames">The frames to stream, in the order given.</param>
internal sealed class FakeSequenceFrameSource(IReadOnlyList<SequenceFrameInput> frames) : ISequenceFrameSource
{
    public async IAsyncEnumerable<SequenceFrameInput> ReadFramesAsync([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        foreach (var frame in frames)
        {
            cancellationToken.ThrowIfCancellationRequested();
            await Task.Yield();
            yield return frame;
        }
    }
}
