namespace Xio.Parallax.Client.Verification.Models;

/// <summary>What admitting a record's verification block decoded: its content hash, its public key when that is a usable 32-byte key,
/// and whether the record declares the legacy canonical version 0, whose manifest and collection preimages this verifier does not implement.</summary>
internal sealed record RecordAdmissionResult(ReadOnlyMemory<byte> ContentHash,
                                             ReadOnlyMemory<byte>? PublicKey,
                                             bool IsLegacy);

/// <summary>Asks for the two image-hash checks.</summary>
internal sealed record XioImageHashCheckRequest(PublishedRecordResponse Record,
                                                ReadOnlyMemory<byte> ContentHash,
                                                ReadOnlyMemory<byte>? OriginalImageBytes);

/// <summary>Asks for one manifest's hash and signature checks; the index labels a manifest that declares no type.</summary>
internal sealed record XioManifestCheckRequest(PublishedRecordResponse_manifests Manifest,
                                               int Index,
                                               RecordAdmissionResult Admission);

/// <summary>One manifest's two checks, and its collection-preimage entry when it declares a type and a hex hash.</summary>
internal sealed record ManifestCheckResult(VerificationCheck HashCheck,
                                           VerificationCheck SignatureCheck,
                                           CanonicalManifestEntry? Entry);

/// <summary>Asks for one Ed25519 signature check over a preimage.</summary>
internal sealed record XioSignatureCheckRequest(string Name,
                                                ReadOnlyMemory<byte>? PublicKey,
                                                ReadOnlyMemory<byte> Preimage,
                                                string? SignatureText);

/// <summary>Asks whether the leaf certificate's key is the record's public key.</summary>
internal sealed record XioLeafKeyCheckRequest(string? LeafPem,
                                              ReadOnlyMemory<byte>? PublicKey);

/// <summary>Asks for the leaf to be chained through the record's certificates to a pinned root at the signing time.</summary>
internal sealed record XioCertificateChainCheckRequest(string? LeafPem,
                                                       IReadOnlyList<string>? ChainPems,
                                                       DateTimeOffset? SignedAtUtc,
                                                       TrustRoots Roots);
