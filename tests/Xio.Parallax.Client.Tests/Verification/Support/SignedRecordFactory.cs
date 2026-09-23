namespace Xio.Parallax.Client.Tests.Verification.Support;

/// <summary>Builds a published record signed by a <see cref="TestPki"/> leaf: <see cref="Create"/> for canonical version 2 (a
/// JUMBF-form <c>c2pa</c> manifest and a JSON-form <c>xi-manifest</c>), <see cref="CreateLegacy"/> for the legacy canonical
/// version 0 shape a production Forensics Lab registration declares.</summary>
internal static class SignedRecordFactory
{
    /// <summary>The original image bytes the record attests.</summary>
    internal static readonly byte[] ImageBytes = Encoding.ASCII.GetBytes("not really a PNG, but bytes all the same");

    /// <summary>The stored bytes of the JUMBF-form c2pa manifest.</summary>
    internal static readonly byte[] C2paBytes = [0x00, 0x00, 0x00, 0x20, 0x6A, 0x75, 0x6D, 0x62, 0x01, 0x02, 0x03, 0x04, 0xFF, 0xFE];

    /// <summary>The carrier's own JUMBF for the JSON-form manifest, which the record never returns.</summary>
    internal static readonly byte[] XiCarrierBytes = Encoding.ASCII.GetBytes("carrier jumbf for the xi manifest");

    /// <summary>The signing time the record declares, inside the test certificates' validity window.</summary>
    internal static readonly DateTimeOffset SignedAt = new(2026, 6, 1, 12, 0, 0, TimeSpan.Zero);

    private static readonly ICanonicalPreimageBuilder Preimages = new CanonicalPreimageBuilder();

    /// <summary>Builds a fully signed record.</summary>
    internal static PublishedRecordResponse Create(TestPki pki)
    {
        var contentHash = Blake3Digest(ImageBytes);
        var c2paHash = Blake3Digest(C2paBytes);
        var xiHash = Blake3Digest(XiCarrierBytes);
        var key = pki.LeafKeys.Private;

        var c2pa = new PublishedRecordResponse_manifests
        {
            Type = "c2pa",
            Form = PublishedRecordResponse_manifests_form.Jumbf,
            Payload = new UntypedString(Convert.ToBase64String(C2paBytes)),
            Hash = Convert.ToHexStringLower(c2paHash),
            Signature = Sign(key, Preimages.Manifest(new XioManifestPreimageRequest(contentHash, "c2pa", c2paHash))),
        };
        var xi = new PublishedRecordResponse_manifests
        {
            Type = "xi-manifest",
            Form = PublishedRecordResponse_manifests_form.Json,
            Payload = new UntypedObject(new Dictionary<string, UntypedNode> { ["title"] = new UntypedString("sunset") }),
            Hash = Convert.ToHexStringLower(xiHash),
            Signature = Sign(key, Preimages.Manifest(new XioManifestPreimageRequest(contentHash, "xi-manifest", xiHash))),
        };
        CanonicalManifestEntry[] entries = [new("c2pa", c2paHash), new("xi-manifest", xiHash)];

        return new PublishedRecordResponse
        {
            OriginalImageHash = Convert.ToHexStringLower(contentHash),
            Outcome = PublishedRecordOutcome.Published,
            Manifests = [c2pa, xi],
            Verification = new PublishedRecordVerification
            {
                CanonicalVersion = 2,
                ContentHash = Convert.ToHexStringLower(contentHash),
                // The literals the harness emits (Xio.Parallax.Harness OrbitalRecordModels): lower-case.
                HashAlgorithm = "blake3-256",
                SignatureAlgorithm = "ed25519",
                SignedAtUtc = SignedAt,
                PublicKey = ToBase64Url(pki.LeafPublicKey),
                Signature = Sign(key, Preimages.Image(contentHash)),
                CollectionSignature = Sign(key, Preimages.Collection(new XioCollectionPreimageRequest(contentHash, entries))),
                LeafCertificate = pki.LeafPem,
                CertificateChain = [pki.RootPem],
                TrustContext = "test",
                TrustVersion = 1,
            },
        };
    }

    /// <summary>Builds a legacy (canonical version 0) record shaped like a production Forensics Lab registration:
    /// a single JUMBF-form <c>c2pa</c> manifest declaring no hash or signature, an upper-case hex <c>contentHash</c>,
    /// and no collection signature. The image signature is still Ed25519 over the content hash bytes alone, so it
    /// is signed the same way a canonical version 2 record's is.</summary>
    internal static PublishedRecordResponse CreateLegacy(TestPki pki)
    {
        var contentHash = Blake3Digest(ImageBytes);
        var key = pki.LeafKeys.Private;

        var c2pa = new PublishedRecordResponse_manifests
        {
            Type = "c2pa",
            Form = PublishedRecordResponse_manifests_form.Jumbf,
            Payload = new UntypedString(Convert.ToBase64String(C2paBytes)),
            Hash = null,
            Signature = null,
        };

        return new PublishedRecordResponse
        {
            OriginalImageHash = Convert.ToHexStringLower(contentHash),
            Outcome = PublishedRecordOutcome.Published,
            Manifests = [c2pa],
            Verification = new PublishedRecordVerification
            {
                CanonicalVersion = 0,
                ContentHash = Convert.ToHexString(contentHash),
                HashAlgorithm = "blake3-256",
                SignatureAlgorithm = "ed25519",
                SignedAtUtc = SignedAt,
                PublicKey = ToBase64Url(pki.LeafPublicKey),
                Signature = Sign(key, Preimages.Image(contentHash)),
                CollectionSignature = null,
                LeafCertificate = pki.LeafPem,
                CertificateChain = [pki.RootPem],
                TrustContext = "xi-forensics-v1",
                TrustVersion = 0,
            },
        };
    }

    /// <summary>Returns the BLAKE3-256 digest of the bytes.</summary>
    internal static byte[] Blake3Digest(byte[] bytes)
    {
        return Blake3Hasher
            .Hash(bytes)
            .AsSpan()
            .ToArray();
    }

    /// <summary>Encodes bytes as unpadded base64url.</summary>
    internal static string ToBase64Url(byte[] bytes)
    {
        return Convert
            .ToBase64String(bytes)
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');
    }

    private static string Sign(AsymmetricKeyParameter privateKey, byte[] message)
    {
        var signer = new Ed25519Signer();
        signer.Init(true, privateKey);
        signer.BlockUpdate(message, 0, message.Length);
        return Convert.ToBase64String(signer.GenerateSignature());
    }
}
