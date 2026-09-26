namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Turns a detected JUMBF manifest store into a manifest part the caller attaches explicitly.</summary>
public static class C2paAttachment
{
    /// <summary>Returns the store as the manifest part manifest[&lt;kind&gt;] of its classified kind, carrying the store bytes unchanged.</summary>
    /// <param name="store">The store detection returned.</param>
    /// <returns>A <see cref="ManifestPart"/> of kind c2pa and form <see cref="ManifestForm.C2pa"/>, or of kind jumbf and form <see cref="ManifestForm.Jumbf"/>.</returns>
    public static ManifestPart AsManifestPart(EmbeddedC2paStore store)
    {
        ArgumentNullException.ThrowIfNull(store);
        return new ManifestPart(store.Kind, FormOf(store.Kind), store.Bytes);
    }

    /// <summary>Returns the wire form of a classified kind: c2pa is sent as application/c2pa, jumbf as application/jumbf; any other kind is refused.</summary>
    /// <param name="kind">The kind the JUMBF walk classified.</param>
    /// <returns>The <see cref="ManifestForm"/> that kind is sent with.</returns>
    internal static ManifestForm FormOf(string kind)
    {
        return kind switch
        {
            C2paConstants.C2paKind => ManifestForm.C2pa,
            C2paConstants.JumbfKind => ManifestForm.Jumbf,
            _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, "Not a classified JUMBF manifest kind; there is no default form."),
        };
    }
}
