namespace Xio.Parallax.Client.Verification.Models;

/// <summary>The pinned root certificates a record's certificate chain must reach; built only by the trust root services, never empty.</summary>
public sealed record TrustRoots
{
    internal TrustRoots(IReadOnlyList<X509Certificate> certificates)
    {
        Certificates = certificates;
    }

    /// <summary>The number of pinned root certificates.</summary>
    public int Count => Certificates.Count;

    /// <summary>The pinned root certificates, parsed.</summary>
    internal IReadOnlyList<X509Certificate> Certificates { get; }
}
