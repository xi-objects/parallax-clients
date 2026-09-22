namespace Xio.Parallax.Client.C2pa.Interfaces;

/// <summary>Detects a C2PA manifest store embedded in an image file's bytes.</summary>
public interface IEmbeddedC2paDetector
{
    /// <summary>Recognises the file's carrier by its signature and extracts its embedded C2PA store.</summary>
    /// <param name="file">The whole file's bytes.</param>
    /// <returns>The carrier, the store when one is embedded and well formed, and a description of the finding.</returns>
    EmbeddedC2paResult Detect(ReadOnlyMemory<byte> file);
}
