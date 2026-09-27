namespace Xio.Parallax.Client.Examples.SequenceFromImages;

// PC-105: the stand-in frame source, a directory of image files in ordinal name order
/// <summary>
/// An <see cref="ISequenceFrameSource"/> over a directory of image files, in ordinal name order:
/// frame ids 1..n, each frame's source time offset the constant frame interval times its
/// position. The stand-in for the ingestion that later decodes a video into frames.
/// </summary>
internal sealed class DirectoryFrameSource : ISequenceFrameSource
{
    private readonly IReadOnlyList<string> _paths;
    private readonly TimeSpan _frameInterval;

    // PC-105: the image extensions this source admits, each with its media type; anything else is refused
    private static readonly IReadOnlyDictionary<string, string> ImageContentTypes = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        [".png"] = "image/png",
        [".jpg"] = "image/jpeg",
        [".jpeg"] = "image/jpeg",
        [".gif"] = "image/gif",
        [".webp"] = "image/webp",
        [".bmp"] = "image/bmp",
    };

    // PC-105: orders the directory's files once, ordinal, refusing any file whose extension is not an image's
    /// <summary>
    /// Builds the source over a directory's files, ordered ordinally by name. A file whose extension is
    /// not a recognised image extension is refused, naming every such file, rather than becoming a frame.
    /// </summary>
    /// <param name="directory">The directory of image files.</param>
    /// <param name="frameInterval">The constant interval between two frames' source time offsets.</param>
    public DirectoryFrameSource(string directory, TimeSpan frameInterval)
    {
        ArgumentException.ThrowIfNullOrEmpty(directory);
        _paths = Directory.EnumerateFiles(directory).OrderBy(path => path, StringComparer.Ordinal).ToList();
        if (_paths.Count == 0)
        {
            throw new InvalidOperationException($"no files under {directory}");
        }

        var unrecognised = _paths.Where(path => !ImageContentTypes.ContainsKey(Path.GetExtension(path))).ToList();
        if (unrecognised.Count > 0)
        {
            throw new InvalidOperationException($"not a recognised image extension: {string.Join(", ", unrecognised.Select(Path.GetFileName))}");
        }

        _frameInterval = frameInterval;
    }

    /// <summary>The directory's file count, the sequence's expected size.</summary>
    public int FrameCount => _paths.Count;

    /// <summary>The first file's path, in ordinal name order, for the round-trip look-up.</summary>
    public string FirstPath => _paths[0];

    // PC-105: the media type of an admitted image file, refusing an unrecognised extension
    /// <summary>The media type of an image file, by its extension; an unrecognised extension is refused.</summary>
    /// <param name="path">The image file's path.</param>
    /// <returns>The file's image media type.</returns>
    public static string ContentTypeFor(string path)
        => ImageContentTypes.TryGetValue(Path.GetExtension(path), out var contentType)
            ? contentType
            : throw new InvalidOperationException($"not a recognised image extension: {Path.GetFileName(path)}");

    // PC-105: yields each file's bytes as one image frame, ids 1..n in ordinal name order
    /// <summary>Reads the directory's files, in ordinal name order, as the sequence's frames.</summary>
    /// <param name="cancellationToken">Cancels the read.</param>
    /// <returns>One frame per file, in ordinal name order.</returns>
    public async IAsyncEnumerable<SequenceFrameInput> ReadFramesAsync([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        for (var index = 0; index < _paths.Count; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var bytes = await File.ReadAllBytesAsync(_paths[index], cancellationToken).ConfigureAwait(false);
            yield return SequenceFrameInput.ForImage(index + 1L, _frameInterval * index, bytes);
        }
    }
}
