namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Checks one manifest's hash against its payload and its Ed25519 signature over the manifest preimage.</summary>
internal interface IManifestChecker
{
    /// <summary>Returns the manifest's hash and signature checks and, when it declares a type and a hex hash, its collection-preimage entry.</summary>
    ManifestCheckResult Check(XioManifestCheckRequest request);
}

internal sealed class ManifestChecker(IVerificationEncoding _encoding,
                                      ICanonicalPreimageBuilder _preimageBuilder,
                                      ISignatureChecker _signatureChecker) : IManifestChecker
{
    public ManifestCheckResult Check(XioManifestCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var manifest = request.Manifest;
        var manifestHash = _encoding.TryHex(manifest.Hash);
        var label = manifest.Type ?? $"#{request.Index}";
        var hashCheck = CheckHash(manifest, VerificationConstants.ManifestHashCheckPrefix + label, manifestHash);
        var signatureName = VerificationConstants.ManifestSignatureCheckPrefix + label;
        if (manifest.Type is null || manifestHash is null)
        {
            var unbuildable = new VerificationCheck(signatureName, VerificationOutcome.Failed, "The manifest declares no type or no hex hash, so its preimage cannot be built.");
            return new ManifestCheckResult(hashCheck, unbuildable, null);
        }

        var preimage = _preimageBuilder.Manifest(new XioManifestPreimageRequest(request.Admission.ContentHash, manifest.Type, manifestHash));
        var signatureCheck = _signatureChecker.Check(new XioSignatureCheckRequest(signatureName, request.Admission.PublicKey, preimage, manifest.Signature));
        return new ManifestCheckResult(hashCheck, signatureCheck, new CanonicalManifestEntry(manifest.Type, manifestHash));
    }

    private VerificationCheck CheckHash(PublishedRecordResponse_manifests manifest, string name, byte[]? manifestHash)
    {
        if (manifestHash is null)
        {
            return new VerificationCheck(name, VerificationOutcome.Failed, "The manifest declares no hex hash.");
        }

        return manifest.Form switch
        {
            PublishedRecordResponse_manifests_form.Json => new VerificationCheck(name, VerificationOutcome.NotRecomputable, "JSON-form manifest: its stored bytes are the carrier's own JUMBF, which the record does not return."),
            PublishedRecordResponse_manifests_form.Jumbf => CheckJumbfHash(manifest, name, manifestHash),
            _ => new VerificationCheck(name, VerificationOutcome.Failed, $"The manifest's form '{manifest.Form?.ToString() ?? VerificationConstants.AbsentValue}' is not one the hash can be established for."),
        };
    }

    private VerificationCheck CheckJumbfHash(PublishedRecordResponse_manifests manifest, string name, byte[] manifestHash)
    {
        var stored = manifest.Payload is UntypedString text ? _encoding.TryBase64(text.GetValue()) : null;
        if (stored is null)
        {
            return new VerificationCheck(name, VerificationOutcome.Failed, "The JUMBF-form payload is not base64 text.");
        }

        return Blake3Hasher.Hash(stored)
                   .AsSpan()
                   .SequenceEqual(manifestHash)
            ? new VerificationCheck(name, VerificationOutcome.Passed, "BLAKE3-256 of the payload bytes equals the manifest hash.")
            : new VerificationCheck(name, VerificationOutcome.Failed, "BLAKE3-256 of the payload bytes differs from the manifest hash.");
    }
}
