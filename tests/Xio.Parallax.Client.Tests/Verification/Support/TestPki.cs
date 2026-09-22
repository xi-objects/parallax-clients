namespace Xio.Parallax.Client.Tests.Verification.Support;

/// <summary>A throwaway Ed25519 certificate authority: a root and a leaf it issued, both valid over a known window.</summary>
internal sealed class TestPki
{
    /// <summary>The common name of the default test root.</summary>
    internal const string DefaultRootName = "Test Parallax Root";

    /// <summary>The start of every certificate's validity window.</summary>
    internal static readonly DateTime NotBefore = new(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);

    /// <summary>The end of every certificate's validity window.</summary>
    internal static readonly DateTime NotAfter = new(2027, 1, 1, 0, 0, 0, DateTimeKind.Utc);

    private static readonly SecureRandom Random = new();

    private TestPki(string rootName)
    {
        var rootKeys = NewKeyPair();
        var intermediateKeys = NewKeyPair();
        LeafKeys = NewKeyPair();
        var rootSubject = new X509Name($"CN={rootName}");
        var intermediateSubject = new X509Name($"CN={rootName} Intermediate");
        var leafSubject = new X509Name("CN=Parallax signing service");
        Root = Issue(new CertificateIssue(rootSubject, rootSubject, rootKeys.Public, rootKeys.Private, IsAuthority: true, Serial: 1));
        Leaf = Issue(new CertificateIssue(rootSubject, leafSubject, LeafKeys.Public, rootKeys.Private, IsAuthority: false, Serial: 2));
        Intermediate = Issue(new CertificateIssue(rootSubject, intermediateSubject, intermediateKeys.Public, rootKeys.Private, IsAuthority: true, Serial: 3));
        IntermediateLeaf = Issue(new CertificateIssue(intermediateSubject, leafSubject, LeafKeys.Public, intermediateKeys.Private, IsAuthority: false, Serial: 4));
    }

    /// <summary>The root certificate.</summary>
    internal X509Certificate Root { get; }

    /// <summary>The leaf certificate the root issued directly.</summary>
    internal X509Certificate Leaf { get; }

    /// <summary>An intermediate CA certificate the root issued.</summary>
    internal X509Certificate Intermediate { get; }

    /// <summary>A leaf certificate, sharing the same key as <see cref="Leaf"/>, that the intermediate issued rather than the root.</summary>
    internal X509Certificate IntermediateLeaf { get; }

    /// <summary>The leaf's key pair, which signs the record.</summary>
    internal AsymmetricCipherKeyPair LeafKeys { get; }

    /// <summary>The root as PEM.</summary>
    internal string RootPem => ToPem(Root);

    /// <summary>The leaf as PEM.</summary>
    internal string LeafPem => ToPem(Leaf);

    /// <summary>The intermediate CA certificate as PEM.</summary>
    internal string IntermediatePem => ToPem(Intermediate);

    /// <summary>The intermediate-issued leaf certificate as PEM.</summary>
    internal string IntermediateLeafPem => ToPem(IntermediateLeaf);

    /// <summary>The leaf's raw 32-byte public key.</summary>
    internal byte[] LeafPublicKey => ((Ed25519PublicKeyParameters)LeafKeys.Public).GetEncoded();

    /// <summary>Creates a new authority whose root has the given common name.</summary>
    internal static TestPki Create(string rootName = DefaultRootName)
    {
        return new TestPki(rootName);
    }

    /// <summary>Generates a fresh Ed25519 key pair.</summary>
    internal static AsymmetricCipherKeyPair NewKeyPair()
    {
        var generator = new Ed25519KeyPairGenerator();
        generator.Init(new Ed25519KeyGenerationParameters(Random));
        return generator.GenerateKeyPair();
    }

    /// <summary>Encodes a certificate as PEM.</summary>
    internal static string ToPem(X509Certificate certificate)
    {
        return "-----BEGIN CERTIFICATE-----\n"
            + Convert.ToBase64String(certificate.GetEncoded(), Base64FormattingOptions.InsertLineBreaks)
            + "\n-----END CERTIFICATE-----\n";
    }

    private static X509Certificate Issue(CertificateIssue issue)
    {
        var generator = new X509V3CertificateGenerator();
        generator.SetSerialNumber(BigInteger.ValueOf(issue.Serial));
        generator.SetIssuerDN(issue.Issuer);
        generator.SetSubjectDN(issue.Subject);
        generator.SetNotBefore(NotBefore);
        generator.SetNotAfter(NotAfter);
        generator.SetPublicKey(issue.SubjectKey);
        generator.AddExtension(X509Extensions.BasicConstraints, true, new BasicConstraints(issue.IsAuthority));
        return generator.Generate(new Asn1SignatureFactory("Ed25519", issue.IssuerKey));
    }

    private sealed record CertificateIssue(X509Name Issuer,
                                           X509Name Subject,
                                           AsymmetricKeyParameter SubjectKey,
                                           AsymmetricKeyParameter IssuerKey,
                                           bool IsAuthority,
                                           long Serial);
}
