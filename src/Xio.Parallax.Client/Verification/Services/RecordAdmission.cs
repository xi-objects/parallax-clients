namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Admits a record's verification block for checking, refusing what this verifier does not implement.</summary>
internal interface IRecordAdmission
{
    /// <summary>Decodes the content hash and public key once the version and algorithms are admitted.</summary>
    /// <exception cref="VerificationRefusedException">A canonical version other than <see cref="VerificationConstants.LegacyCanonicalVersion"/> (0) or <see cref="VerificationConstants.ImplementedCanonicalVersion"/> (2), an unimplemented hash or signature algorithm, or a content hash that is not a BLAKE3-256 hex digest.</exception>
    RecordAdmissionResult Admit(PublishedRecordVerification verification);
}

internal sealed class RecordAdmission(IVerificationEncoding _encoding) : IRecordAdmission
{
    public RecordAdmissionResult Admit(PublishedRecordVerification verification)
    {
        ArgumentNullException.ThrowIfNull(verification);
        var isLegacy = verification.CanonicalVersion == VerificationConstants.LegacyCanonicalVersion;
        if (!isLegacy && verification.CanonicalVersion != VerificationConstants.ImplementedCanonicalVersion)
        {
            throw new VerificationRefusedException($"Canonical version {verification.CanonicalVersion?.ToString() ?? VerificationConstants.AbsentValue} is not implemented; only {VerificationConstants.LegacyCanonicalVersion} (legacy) and {VerificationConstants.ImplementedCanonicalVersion} are.");
        }

        if (!string.Equals(verification.HashAlgorithm, VerificationConstants.ImplementedHashAlgorithm, StringComparison.OrdinalIgnoreCase))
        {
            throw new VerificationRefusedException($"Hash algorithm '{verification.HashAlgorithm ?? VerificationConstants.AbsentValue}' is not implemented; only {VerificationConstants.ImplementedHashAlgorithm} is.");
        }

        if (!string.Equals(verification.SignatureAlgorithm, VerificationConstants.ImplementedSignatureAlgorithm, StringComparison.OrdinalIgnoreCase))
        {
            throw new VerificationRefusedException($"Signature algorithm '{verification.SignatureAlgorithm ?? VerificationConstants.AbsentValue}' is not implemented; only {VerificationConstants.ImplementedSignatureAlgorithm} is.");
        }

        var contentHash = _encoding.TryHex(verification.ContentHash);
        if (contentHash is null || contentHash.Length != VerificationConstants.Blake3HashLength)
        {
            throw new VerificationRefusedException("The record's contentHash is not a 32-byte hex BLAKE3-256 digest.");
        }

        var publicKey = _encoding.TryBase64Url(verification.PublicKey);
        var usableKey = publicKey is not null && publicKey.Length == VerificationConstants.Ed25519PublicKeyLength
            ? new ReadOnlyMemory<byte>(publicKey)
            : (ReadOnlyMemory<byte>?)null;
        return new RecordAdmissionResult(contentHash, usableKey, isLegacy);
    }
}
