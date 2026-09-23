namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Verifies a published record's hashes, Ed25519 signatures and certificate chain offline against pinned roots, returning a verdict per check.</summary>
public interface IAttributionVerifier
{
    /// <summary>Verifies a published record.</summary>
    /// <returns>The verdict of every check.</returns>
    /// <exception cref="VerificationRefusedException">No roots, no verification block, an unimplemented hash or signature algorithm, a canonical version other than 0 (legacy) or 2, or a content hash that is not a BLAKE3-256 hex digest.</exception>
    VerificationReport Verify(XioVerifyRecordRequest request);
}

/// <summary>The attribution verifier over the built-in checks.</summary>
public sealed class AttributionVerifier : IAttributionVerifier
{
    private readonly IRecordAdmission _admission;
    private readonly IImageHashChecker _imageHashChecker;
    private readonly IManifestChecker _manifestChecker;
    private readonly ISignatureChecker _signatureChecker;
    private readonly ICanonicalPreimageBuilder _preimageBuilder;
    private readonly ICertificateChainValidator _chainValidator;

    /// <summary>Creates the verifier over the built-in checks.</summary>
    public AttributionVerifier()
        : this(VerificationComposition.Admission,
               VerificationComposition.ImageHashChecker,
               VerificationComposition.ManifestChecker,
               VerificationComposition.SignatureChecker,
               VerificationComposition.PreimageBuilder,
               VerificationComposition.ChainValidator)
    {
    }

    internal AttributionVerifier(IRecordAdmission admission,
                                 IImageHashChecker imageHashChecker,
                                 IManifestChecker manifestChecker,
                                 ISignatureChecker signatureChecker,
                                 ICanonicalPreimageBuilder preimageBuilder,
                                 ICertificateChainValidator chainValidator)
    {
        _admission = admission;
        _imageHashChecker = imageHashChecker;
        _manifestChecker = manifestChecker;
        _signatureChecker = signatureChecker;
        _preimageBuilder = preimageBuilder;
        _chainValidator = chainValidator;
    }

    /// <inheritdoc/>
    public VerificationReport Verify(XioVerifyRecordRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var record = request.Record;
        ArgumentNullException.ThrowIfNull(record, nameof(request.Record));
        if (request.Roots is null || request.Roots.Count == 0)
        {
            throw new VerificationRefusedException("No trust roots: the certificate chain cannot be checked, so the record is not verified.");
        }

        var verification = record.Verification
            ?? throw new VerificationRefusedException("The record carries no verification block.");
        var admission = _admission.Admit(verification);

        var checks = new List<VerificationCheck>();
        checks.AddRange(_imageHashChecker.Check(new XioImageHashCheckRequest(record, admission.ContentHash, request.OriginalImageBytes)));
        checks.AddRange(CheckManifestsAndCollection(record, verification, admission));
        checks.Add(_signatureChecker.Check(new XioSignatureCheckRequest(VerificationConstants.ImageSignatureCheck, admission.PublicKey, _preimageBuilder.Image(admission.ContentHash), verification.Signature)));
        checks.Add(_chainValidator.CheckLeafKey(new XioLeafKeyCheckRequest(verification.LeafCertificate, admission.PublicKey)));
        checks.Add(_chainValidator.CheckChain(new XioCertificateChainCheckRequest(verification.LeafCertificate, verification.CertificateChain, verification.SignedAtUtc, request.Roots)));
        return new VerificationReport(checks);
    }

    private List<VerificationCheck> CheckManifestsAndCollection(PublishedRecordResponse record, PublishedRecordVerification verification, RecordAdmissionResult admission)
    {
        var checks = new List<VerificationCheck>();
        var manifests = record.Manifests ?? [];
        var entries = new List<CanonicalManifestEntry>();
        var collectable = true;
        for (var index = 0; index < manifests.Count; index++)
        {
            var result = _manifestChecker.Check(new XioManifestCheckRequest(manifests[index], index, admission));
            checks.Add(result.HashCheck);
            checks.Add(result.SignatureCheck);
            if (result.Entry is null)
            {
                collectable = false;
            }
            else
            {
                entries.Add(result.Entry);
            }
        }

        checks.Add(CollectionSignatureCheck(collectable, manifests.Count, admission, verification, entries));
        return checks;
    }

    private VerificationCheck CollectionSignatureCheck(bool collectable, int manifestCount, RecordAdmissionResult admission, PublishedRecordVerification verification, List<CanonicalManifestEntry> entries)
    {
        if (admission.IsLegacy)
        {
            return string.IsNullOrEmpty(verification.CollectionSignature)
                ? new VerificationCheck(VerificationConstants.CollectionSignatureCheck, VerificationOutcome.NotPerformed, VerificationConstants.LegacyCollectionSignatureAbsentDetail)
                : new VerificationCheck(VerificationConstants.CollectionSignatureCheck, VerificationOutcome.NotRecomputable, VerificationConstants.LegacyCollectionHashingUnimplementedDetail);
        }

        if (!collectable)
        {
            return new VerificationCheck(VerificationConstants.CollectionSignatureCheck, VerificationOutcome.Failed, "A manifest declares no type or no hex hash, so the collection preimage cannot be built.");
        }

        if (manifestCount == 0 && string.IsNullOrEmpty(verification.CollectionSignature))
        {
            return new VerificationCheck(VerificationConstants.CollectionSignatureCheck, VerificationOutcome.NotPerformed, "The record carries no manifests, so there is no collection to sign.");
        }

        return _signatureChecker.Check(new XioSignatureCheckRequest(VerificationConstants.CollectionSignatureCheck, admission.PublicKey, _preimageBuilder.Collection(new XioCollectionPreimageRequest(admission.ContentHash, entries)), verification.CollectionSignature));
    }
}
