namespace Xio.Parallax.Client.Verification;

/// <summary>The algorithms, version, lengths, Orbital route and check names the attribution verifier implements.</summary>
public static class VerificationConstants
{
    /// <summary>The only content-hash algorithm implemented.</summary>
    public const string ImplementedHashAlgorithm = "BLAKE3-256";

    /// <summary>The only signature algorithm implemented (compared case-insensitively).</summary>
    public const string ImplementedSignatureAlgorithm = "Ed25519";

    /// <summary>The only canonical preimage version implemented; its byte leads the manifest and collection preimages.</summary>
    public const byte ImplementedCanonicalVersion = 0x02;

    /// <summary>The byte length of a BLAKE3-256 digest.</summary>
    public const int Blake3HashLength = 32;

    /// <summary>The byte length of a raw Ed25519 public key.</summary>
    public const int Ed25519PublicKeyLength = 32;

    /// <summary>The byte length of an Ed25519 signature.</summary>
    public const int Ed25519SignatureLength = 64;

    /// <summary>The Orbital discovery route that answers the pinned roots.</summary>
    public const string OrbitalInfoPath = "/info";

    /// <summary>The Orbital discovery property that carries the pinned root PEMs (matched case-insensitively).</summary>
    public const string OrbitalPinnedRootsProperty = "pinnedRoots";

    /// <summary>The name of the check of the original bytes' SHA-256 against <c>originalImageHash</c>.</summary>
    public const string OriginalImageHashCheck = "originalImageHash";

    /// <summary>The name of the check of the original bytes' BLAKE3-256 against <c>contentHash</c>.</summary>
    public const string ContentHashCheck = "contentHash";

    /// <summary>The prefix of each manifest's hash check; the manifest's type (or <c>#index</c>) follows.</summary>
    public const string ManifestHashCheckPrefix = "manifestHash:";

    /// <summary>The prefix of each manifest's signature check; the manifest's type (or <c>#index</c>) follows.</summary>
    public const string ManifestSignatureCheckPrefix = "manifestSignature:";

    /// <summary>The name of the collection signature check.</summary>
    public const string CollectionSignatureCheck = "collectionSignature";

    /// <summary>The name of the image signature check.</summary>
    public const string ImageSignatureCheck = "imageSignature";

    /// <summary>The name of the check that the leaf certificate's key is the record's public key.</summary>
    public const string LeafKeyCheck = "leafKeyMatchesPublicKey";

    /// <summary>The name of the certificate chain check.</summary>
    public const string CertificateChainCheck = "certificateChain";

    /// <summary>The stand-in for an absent value in a check's detail or a refusal's message.</summary>
    internal const string AbsentValue = "(none)";

    /// <summary>The detail of every check that needs the public key when the record carries no usable one.</summary>
    internal const string PublicKeyUnusableDetail = "The record's publicKey is absent or not a 32-byte base64url key.";

    /// <summary>The detail of every check that needs the leaf certificate when the record carries no single one.</summary>
    internal const string LeafCertificateUnusableDetail = "The record's leafCertificate is absent or is not exactly one PEM certificate.";
}
