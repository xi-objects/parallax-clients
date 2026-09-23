namespace Xio.Parallax.Client.Tests.Verification.Services;

public sealed class AttributionVerifierTests
{
    private readonly TestPki _pki = TestPki.Create();
    private readonly IAttributionVerifier _verifier = new AttributionVerifier();
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public void A_faithful_record_passes_every_performed_check()
    {
        var report = Verify(SignedRecordFactory.Create(_pki), SignedRecordFactory.ImageBytes);

        Assert.False(report.AnyFailed);
        Assert.True(report.AllPerformedPassed);
        Assert.False(report.AllPassed);
        string[] expected =
        [
            "originalImageHash", "contentHash",
            "manifestHash:c2pa", "manifestSignature:c2pa",
            "manifestHash:xi-manifest", "manifestSignature:xi-manifest",
            "collectionSignature", "imageSignature", "leafKeyMatchesPublicKey", "certificateChain",
        ];
        Assert.Equal(expected, report.Checks.Select(c => c.Name));
        Assert.All(report.Checks.Where(c => c.Name != "manifestHash:xi-manifest"), c => Assert.Equal(VerificationOutcome.Passed, c.Outcome));
    }

    [Fact]
    public void A_json_form_manifest_hash_is_not_recomputable_never_passed()
    {
        var report = Verify(SignedRecordFactory.Create(_pki), SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "manifestHash:xi-manifest"));
        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "manifestSignature:xi-manifest"));
    }

    [Fact]
    public void Without_the_original_bytes_originalImageHash_still_passes_but_contentHash_is_not_performed()
    {
        var report = Verify(SignedRecordFactory.Create(_pki), null);

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "originalImageHash"));
        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "contentHash"));
        Assert.True(report.AllPerformedPassed);
    }

    [Fact]
    public void Different_original_bytes_fail_only_contentHash()
    {
        var report = Verify(SignedRecordFactory.Create(_pki), [0x01, 0x02]);

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "originalImageHash"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "contentHash"));
        Assert.True(report.AnyFailed);
    }

    [Fact]
    public void An_originalImageHash_that_disagrees_with_contentHash_fails_regardless_of_bytes()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.OriginalImageHash = Convert.ToHexStringLower(SignedRecordFactory.Blake3Digest([0xAA]));

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "originalImageHash"));
        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "contentHash"));
    }

    [Fact]
    public void A_tampered_manifest_payload_byte_fails_its_hash()
    {
        var record = SignedRecordFactory.Create(_pki);
        var tampered = (byte[])SignedRecordFactory.C2paBytes.Clone();
        tampered[5] ^= 0x01;
        record.Manifests![0].Payload = new UntypedString(Convert.ToBase64String(tampered));

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "manifestHash:c2pa"));
    }

    [Fact]
    public void A_tampered_payload_restated_under_its_new_hash_fails_the_signatures()
    {
        var record = SignedRecordFactory.Create(_pki);
        var tampered = (byte[])SignedRecordFactory.C2paBytes.Clone();
        tampered[5] ^= 0x01;
        record.Manifests![0].Payload = new UntypedString(Convert.ToBase64String(tampered));
        record.Manifests[0].Hash = Convert.ToHexStringLower(SignedRecordFactory.Blake3Digest(tampered));

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "manifestHash:c2pa"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "manifestSignature:c2pa"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "collectionSignature"));
    }

    [Fact]
    public void A_tampered_manifest_hash_byte_fails_its_hash_and_its_signature()
    {
        var record = SignedRecordFactory.Create(_pki);
        var hash = Convert.FromHexString(record.Manifests![0].Hash!);
        hash[0] ^= 0x01;
        record.Manifests[0].Hash = Convert.ToHexStringLower(hash);

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "manifestHash:c2pa"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "manifestSignature:c2pa"));
    }

    [Fact]
    public void A_stripped_manifest_fails_the_collection_signature()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Manifests!.RemoveAt(1);

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "collectionSignature"));
        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "manifestSignature:c2pa"));
    }

    [Fact]
    public void Manifests_present_but_the_collection_signature_removed_fails_the_collection_check()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.CollectionSignature = null;

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "collectionSignature"));
    }

    [Fact]
    public void No_manifests_and_no_collection_signature_is_not_performed()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Manifests!.Clear();
        record.Verification!.CollectionSignature = null;

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "collectionSignature"));
        Assert.False(report.AnyFailed);
    }

    [Fact]
    public void A_wrong_public_key_fails_the_leaf_key_match_and_every_signature()
    {
        var record = SignedRecordFactory.Create(_pki);
        var other = ((Ed25519PublicKeyParameters)TestPki.NewKeyPair().Public).GetEncoded();
        record.Verification!.PublicKey = SignedRecordFactory.ToBase64Url(other);

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "leafKeyMatchesPublicKey"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "imageSignature"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "collectionSignature"));
    }

    [Fact]
    public void A_padded_standard_base64_public_key_is_accepted()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.PublicKey = Convert.ToBase64String(_pki.LeafPublicKey);

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.False(report.AnyFailed);
    }

    [Fact]
    public void A_tampered_image_signature_fails()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.Signature = record.Verification.CollectionSignature;

        var report = Verify(record, SignedRecordFactory.ImageBytes);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "imageSignature"));
    }

    [Fact]
    public void An_unknown_hash_algorithm_is_refused_by_name()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.HashAlgorithm = "SHA3-256";

        var refusal = Assert.Throws<VerificationRefusedException>(() => Verify(record, null));

        Assert.Contains("SHA3-256", refusal.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Canonical_version_1_is_refused()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.CanonicalVersion = 1;

        Assert.Throws<VerificationRefusedException>(() => Verify(record, null));
    }

    [Fact]
    public void An_unknown_signature_algorithm_is_refused()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.SignatureAlgorithm = "ECDSA-P256";

        Assert.Throws<VerificationRefusedException>(() => Verify(record, null));
    }

    [Fact]
    public void Verifying_with_no_roots_is_refused()
    {
        Assert.Throws<VerificationRefusedException>(() => VerifyUnder(SignedRecordFactory.Create(_pki), null!));
    }

    [Fact]
    public void A_legacy_canonical_version_0_record_passes_the_image_signature_and_chain_but_never_the_manifest_or_collection()
    {
        var report = Verify(SignedRecordFactory.CreateLegacy(_pki), null);

        Assert.False(report.AnyFailed);
        Assert.True(report.AllPerformedPassed);
        Assert.False(report.AllPassed);
        string[] mustPass = ["originalImageHash", "imageSignature", "leafKeyMatchesPublicKey", "certificateChain"];
        Assert.All(mustPass, name => Assert.Equal(VerificationOutcome.Passed, Outcome(report, name)));
        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "contentHash"));
        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "manifestHash:c2pa"));
        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "manifestSignature:c2pa"));
        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "collectionSignature"));
    }

    [Fact]
    public void A_legacy_record_with_a_tampered_image_signature_byte_fails()
    {
        var record = SignedRecordFactory.CreateLegacy(_pki);
        var signature = Convert.FromBase64String(record.Verification!.Signature!);
        signature[0] ^= 0x01;
        record.Verification.Signature = Convert.ToBase64String(signature);

        var report = Verify(record, null);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "imageSignature"));
    }

    [Fact]
    public void A_legacy_record_declaring_a_canonical_version_1_is_still_refused()
    {
        var record = SignedRecordFactory.CreateLegacy(_pki);
        record.Verification!.CanonicalVersion = 1;

        Assert.Throws<VerificationRefusedException>(() => Verify(record, null));
    }

    [Fact]
    public void A_legacy_record_carrying_a_collection_signature_is_not_recomputable_never_passed()
    {
        var record = SignedRecordFactory.CreateLegacy(_pki);
        record.Verification!.CollectionSignature = record.Verification.Signature;

        var report = Verify(record, null);

        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "collectionSignature"));
    }

    private VerificationReport Verify(PublishedRecordResponse record, byte[]? originalBytes)
    {
        ReadOnlyMemory<byte>? bytes = originalBytes is null ? (ReadOnlyMemory<byte>?)null : originalBytes;
        return _verifier.Verify(new XioVerifyRecordRequest(record, bytes, _reader.FromPem([_pki.RootPem])));
    }

    private VerificationReport VerifyUnder(PublishedRecordResponse record, TrustRoots roots)
    {
        return _verifier.Verify(new XioVerifyRecordRequest(record, SignedRecordFactory.ImageBytes, roots));
    }

    private static VerificationOutcome Outcome(VerificationReport report, string name)
    {
        var check = report.Find(name);
        Assert.NotNull(check);
        return check.Outcome;
    }
}
