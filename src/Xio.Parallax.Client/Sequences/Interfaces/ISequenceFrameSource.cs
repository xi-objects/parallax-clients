namespace Xio.Parallax.Client.Sequences.Interfaces;

// PC-102: the frame source contract a later ingestion implements
/// <summary>
/// A source of the frames that make up one sequence, in chain order. The source owns the frame
/// ids it hands out: they are monotone, and room between them is allowed, but the source says
/// nothing about the links between frames. The client derives every frame's prev from the frame
/// read immediately before it (the sequence's HEAD id for the first frame) and its next from the
/// frame read immediately after it. A frame's source time offset is its position within its own
/// media, not a wall-clock time.
/// </summary>
public interface ISequenceFrameSource
{
    // PC-102: streams the source's frames in chain order
    /// <summary>Reads the source's frames, in chain order.</summary>
    /// <param name="cancellationToken">Cancels the read.</param>
    /// <returns>The source's frames, in chain order.</returns>
    IAsyncEnumerable<SequenceFrameInput> ReadFramesAsync(CancellationToken cancellationToken);
}
