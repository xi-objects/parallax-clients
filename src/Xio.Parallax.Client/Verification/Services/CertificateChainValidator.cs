namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Checks the record's leaf key and chains its leaf certificate to a pinned root with BouncyCastle.</summary>
internal interface ICertificateChainValidator
{
    /// <summary>Checks that the leaf certificate's raw Ed25519 key equals the record's public key.</summary>
    VerificationCheck CheckLeafKey(XioLeafKeyCheckRequest request);

    /// <summary>Chains the leaf through the record's certificates to a pinned root, every certificate valid at the signing time.</summary>
    VerificationCheck CheckChain(XioCertificateChainCheckRequest request);
}

internal sealed class CertificateChainValidator(IPemCertificateParser _parser) : ICertificateChainValidator
{
    public VerificationCheck CheckLeafKey(XioLeafKeyCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.PublicKey is not { } publicKey)
        {
            return Fail(VerificationConstants.LeafKeyCheck, VerificationConstants.PublicKeyUnusableDetail);
        }

        var leaf = _parser.Parse(request.LeafPem);
        if (leaf.Count != 1)
        {
            return Fail(VerificationConstants.LeafKeyCheck, VerificationConstants.LeafCertificateUnusableDetail);
        }

        if (leaf[0].GetPublicKey() is not Ed25519PublicKeyParameters leafKey)
        {
            return Fail(VerificationConstants.LeafKeyCheck, "The leaf certificate's key is not an Ed25519 key.");
        }

        return leafKey.GetEncoded()
                   .AsSpan()
                   .SequenceEqual(publicKey.Span)
            ? new VerificationCheck(VerificationConstants.LeafKeyCheck, VerificationOutcome.Passed, "The leaf certificate's Ed25519 key equals publicKey.")
            : Fail(VerificationConstants.LeafKeyCheck, "The leaf certificate's Ed25519 key differs from publicKey.");
    }

    public VerificationCheck CheckChain(XioCertificateChainCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var leaf = _parser.Parse(request.LeafPem);
        if (leaf.Count != 1)
        {
            return Fail(VerificationConstants.CertificateChainCheck, VerificationConstants.LeafCertificateUnusableDetail);
        }

        if (request.SignedAtUtc is not { } signedAtUtc)
        {
            return Fail(VerificationConstants.CertificateChainCheck, "The record declares no signedAtUtc to check validity at.");
        }

        var intermediates = new List<X509Certificate>();
        foreach (var pem in request.ChainPems ?? [])
        {
            var parsed = _parser.Parse(pem);
            if (parsed.Count == 0)
            {
                return Fail(VerificationConstants.CertificateChainCheck, "A certificateChain entry is not a PEM certificate.");
            }

            intermediates.AddRange(parsed);
        }

        return Walk(leaf[0], intermediates, signedAtUtc, request.Roots);
    }

    private static VerificationCheck Walk(X509Certificate leaf, List<X509Certificate> intermediates, DateTimeOffset signedAtUtc, TrustRoots roots)
    {
        var at = signedAtUtc.UtcDateTime;
        var used = new HashSet<X509Certificate>();
        var current = leaf;
        for (var depth = 0; depth <= intermediates.Count; depth++)
        {
            if (!current.IsValid(at))
            {
                return Fail(VerificationConstants.CertificateChainCheck, $"{current.SubjectDN} is not valid at {signedAtUtc:O}.");
            }

            if (roots.Certificates.Any(root => root.Equals(current)))
            {
                return Pass(current);
            }

            var root = roots.Certificates.FirstOrDefault(candidate => Issued(candidate, current));
            if (root is not null)
            {
                return root.IsValid(at)
                    ? Pass(root)
                    : Fail(VerificationConstants.CertificateChainCheck, $"Pinned root {root.SubjectDN} is not valid at {signedAtUtc:O}.");
            }

            var issuer = intermediates.FirstOrDefault(candidate => !used.Contains(candidate) && candidate.GetBasicConstraints() >= 0 && Issued(candidate, current));
            if (issuer is null)
            {
                return Fail(VerificationConstants.CertificateChainCheck, $"No pinned root or chain certificate issued {current.SubjectDN}.");
            }

            used.Add(issuer);
            current = issuer;
        }

        return Fail(VerificationConstants.CertificateChainCheck, "The chain does not reach a pinned root.");
    }

    private static bool Issued(X509Certificate issuer, X509Certificate subject)
    {
        if (!issuer.SubjectDN.Equivalent(subject.IssuerDN))
        {
            return false;
        }

        try
        {
            subject.Verify(issuer.GetPublicKey());
            return true;
        }
        catch (Exception exception) when (exception is Org.BouncyCastle.Security.GeneralSecurityException or Org.BouncyCastle.Crypto.CryptoException or ArgumentException or InvalidOperationException)
        {
            return false;
        }
    }

    private static VerificationCheck Pass(X509Certificate root)
    {
        return new VerificationCheck(VerificationConstants.CertificateChainCheck, VerificationOutcome.Passed, $"The leaf chains to pinned root {root.SubjectDN}, every certificate valid at the signing time.");
    }

    private static VerificationCheck Fail(string name, string detail)
    {
        return new VerificationCheck(name, VerificationOutcome.Failed, detail);
    }
}
