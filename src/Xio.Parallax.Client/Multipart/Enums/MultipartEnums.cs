namespace Xio.Parallax.Client.Multipart.Enums;

/// <summary>
/// The wire content type a manifest part is sent with. There is no default: every manifest
/// states its own form.
/// </summary>
public enum ManifestForm
{
    /// <summary>The manifest bytes are a JSON document, sent as application/json.</summary>
    Json,

    /// <summary>The manifest bytes are a JUMBF box, sent as application/jumbf.</summary>
    Jumbf,

    /// <summary>The manifest bytes are a C2PA store, sent as application/c2pa.</summary>
    C2pa,
}
