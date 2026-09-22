namespace Xio.Parallax.Client.Verification.Interfaces;

/// <summary>Parses PEM text into certificates.</summary>
internal interface IPemCertificateParser
{
    /// <summary>Parses every certificate in a PEM text; an absent or unparseable text yields none.</summary>
    IReadOnlyList<X509Certificate> Parse(string? pem);
}
