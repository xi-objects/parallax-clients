namespace Xio.Parallax.Client.Multipart.Services;

/// <summary>Converts a <see cref="ManifestForm"/> to the wire content type it stands for.</summary>
internal static class ManifestFormExtensions
{
    // REST-CONTRACTS 0.1.0: each form's media type is the API's own ImageManifestContentTypes constant
    /// <summary>
    /// Returns the content type this form is sent with. There is no default for an unrecognized
    /// value: it is a programming error, never a guess.
    /// </summary>
    /// <param name="form">The manifest form to convert.</param>
    /// <returns>The wire content type, for example application/jumbf.</returns>
    internal static string ToContentType(this ManifestForm form)
    {
        return form switch
        {
            ManifestForm.Json => ImageManifestContentTypes.JsonMediaType,
            ManifestForm.Jumbf => ImageManifestContentTypes.JumbfMediaType,
            ManifestForm.C2pa => ImageManifestContentTypes.C2paMediaType,
            _ => throw new ArgumentOutOfRangeException(nameof(form), form, "Unknown manifest form; there is no default content type."),
        };
    }
}
