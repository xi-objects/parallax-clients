namespace Xio.Parallax.Client.Verification.Services;

internal sealed class PemCertificateParser : IPemCertificateParser
{
    public IReadOnlyList<X509Certificate> Parse(string? pem)
    {
        if (string.IsNullOrWhiteSpace(pem))
        {
            return [];
        }

        try
        {
            return [.. new X509CertificateParser().ReadCertificates(Encoding.ASCII.GetBytes(pem))];
        }
        catch (Exception exception) when (exception is Org.BouncyCastle.Security.Certificates.CertificateException or IOException or ArgumentException)
        {
            return [];
        }
    }
}
