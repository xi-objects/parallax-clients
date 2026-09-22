namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Pins root certificates from PEM text or a PEM file.</summary>
public interface ITrustRootReader
{
    /// <summary>Pins the root certificates in the given PEM texts; each text may carry one or more certificates.</summary>
    /// <exception cref="VerificationRefusedException">No certificate is given, or a text carries none.</exception>
    TrustRoots FromPem(IEnumerable<string> pems);

    /// <summary>Pins the root certificates in a PEM file.</summary>
    /// <exception cref="VerificationRefusedException">The file carries no certificate.</exception>
    TrustRoots FromPemFile(string path);
}

/// <summary>Pins root certificates from PEM text or a PEM file.</summary>
public sealed class TrustRootReader : ITrustRootReader
{
    private readonly IPemCertificateParser _parser;

    /// <summary>Creates the reader over the built-in PEM parser.</summary>
    public TrustRootReader()
        : this(VerificationComposition.PemParser)
    {
    }

    internal TrustRootReader(IPemCertificateParser parser)
    {
        _parser = parser;
    }

    /// <inheritdoc/>
    public TrustRoots FromPem(IEnumerable<string> pems)
    {
        ArgumentNullException.ThrowIfNull(pems);
        var certificates = new List<X509Certificate>();
        var index = 0;
        foreach (var pem in pems)
        {
            var parsed = _parser.Parse(pem);
            if (parsed.Count == 0)
            {
                throw new VerificationRefusedException($"Trust root {index} carries no PEM certificate.");
            }

            certificates.AddRange(parsed);
            index++;
        }

        if (certificates.Count == 0)
        {
            throw new VerificationRefusedException("No trust roots: at least one pinned root certificate is required.");
        }

        return new TrustRoots(certificates);
    }

    /// <inheritdoc/>
    public TrustRoots FromPemFile(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        return FromPem([File.ReadAllText(path)]);
    }
}
