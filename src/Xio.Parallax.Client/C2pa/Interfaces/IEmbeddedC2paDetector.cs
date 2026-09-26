namespace Xio.Parallax.Client.C2pa.Interfaces;

/// <summary>Detects the JUMBF manifest stores embedded in an image file's bytes, each classified c2pa or jumbf.</summary>
public interface IEmbeddedC2paDetector
{
    /// <summary>Recognises the file's carrier by its signature and extracts and classifies every embedded JUMBF manifest store.</summary>
    /// <param name="file">The whole file's bytes.</param>
    /// <returns>The carrier, the outcome, every well-formed store in document order when found, and a description of the finding.</returns>
    EmbeddedC2paResult Detect(ReadOnlyMemory<byte> file);
}
