namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Turns a detected C2PA store into a manifest part the caller attaches explicitly.</summary>
public static class C2paAttachment
{
    /// <summary>Returns the store as the manifest part manifest[c2pa], in the C2PA form, carrying the store bytes unchanged.</summary>
    /// <param name="store">The store detection returned.</param>
    /// <returns>A <see cref="ManifestPart"/> of kind c2pa and form <see cref="ManifestForm.C2pa"/>.</returns>
    public static ManifestPart AsManifestPart(EmbeddedC2paStore store)
    {
        ArgumentNullException.ThrowIfNull(store);
        return new ManifestPart(C2paConstants.AttachmentKind, ManifestForm.C2pa, store.Bytes);
    }
}
