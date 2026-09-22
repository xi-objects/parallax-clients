namespace Xio.Parallax.Client.Multipart.Models;

/// <summary>One image to send: its file name, its content type, and its raw bytes.</summary>
/// <param name="FileName">The file name reported in the multipart part.</param>
/// <param name="ContentType">The image's media type, for example image/png.</param>
/// <param name="Bytes">The image's raw bytes.</param>
public sealed record ImageUpload(string FileName,
                                  string ContentType,
                                  ReadOnlyMemory<byte> Bytes)
{
    /// <summary>
    /// Reads an image from disk, using its file name from <paramref name="path"/> and the given
    /// content type.
    /// </summary>
    /// <param name="path">The path to read the image bytes from.</param>
    /// <param name="contentType">The image's media type, for example image/png.</param>
    /// <returns>An <see cref="ImageUpload"/> carrying the file's bytes.</returns>
    public static ImageUpload FromFile(string path, string contentType)
    {
        ArgumentException.ThrowIfNullOrEmpty(path);
        ArgumentException.ThrowIfNullOrEmpty(contentType);
        var bytes = File.ReadAllBytes(path);
        return new ImageUpload(Path.GetFileName(path), contentType, bytes);
    }
}

/// <summary>
/// One manifest attached to an image: its kind, the form its bytes are sent in, and the bytes
/// themselves. Becomes the wire part manifest[&lt;kind&gt;].
/// </summary>
/// <param name="Kind">
/// The manifest's kind, validated against ^[A-Za-z0-9._-]{1,64}$ before anything is sent.
/// </param>
/// <param name="Form">The content type the manifest bytes are sent with.</param>
/// <param name="Bytes">The manifest's raw bytes.</param>
public sealed record ManifestPart(string Kind,
                                   ManifestForm Form,
                                   ReadOnlyMemory<byte> Bytes)
{
    private static readonly Regex KindPattern = new("^[A-Za-z0-9._-]{1,64}$", RegexOptions.Compiled);

    /// <summary>The manifest's kind, validated against ^[A-Za-z0-9._-]{1,64}$.</summary>
    public string Kind { get; } = ValidateKind(Kind);

    private static string ValidateKind(string kind)
    {
        ArgumentNullException.ThrowIfNull(kind);
        if (!KindPattern.IsMatch(kind))
        {
            throw new ArgumentException($"Manifest kind '{kind}' must match ^[A-Za-z0-9._-]{{1,64}}$.", nameof(kind));
        }

        return kind;
    }
}

/// <summary>One image paired with the manifests that precede it on the wire.</summary>
/// <param name="Image">The image itself.</param>
/// <param name="Manifests">The manifests to send immediately before the image's part, in order.</param>
internal sealed record ManifestedImage(ImageUpload Image,
                                        IReadOnlyList<ManifestPart> Manifests);
