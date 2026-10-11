namespace Xio.Parallax.Client.Multipart.Services;

/// <summary>Converts a <see cref="ManifestForm"/> to the wire content type it stands for.</summary>
internal static class ManifestFormExtensions
{
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
            ManifestForm.Json => "application/json",
            ManifestForm.Jumbf => "application/jumbf",
            ManifestForm.C2pa => "application/c2pa",
            _ => throw new ArgumentOutOfRangeException(nameof(form), form, "Unknown manifest form; there is no default content type."),
        };
    }
}
