namespace Xio.Parallax.Client.Tests.Verification.Services;

/// <summary>The <c>certificateChain</c> check, split out from <see cref="AttributionVerifierTests"/> to keep files under the line limit: pinned roots, multi-certificate chains and validity windows.</summary>
public sealed class CertificateChainCheckTests
{
    private readonly TestPki _pki = TestPki.Create();
    private readonly IAttributionVerifier _verifier = new AttributionVerifier();
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public void A_wrong_root_fails_the_certificate_chain()
    {
        var stranger = TestPki.Create("Some Other Root");

        var report = VerifyUnder(SignedRecordFactory.Create(_pki), _reader.FromPem([stranger.RootPem]));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_root_with_the_pinned_name_but_another_key_fails_the_certificate_chain()
    {
        var impostor = TestPki.Create(TestPki.DefaultRootName);

        var report = VerifyUnder(SignedRecordFactory.Create(_pki), _reader.FromPem([impostor.RootPem]));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_leaf_intermediate_root_chain_passes_with_the_root_pinned()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.LeafCertificate = _pki.IntermediateLeafPem;
        record.Verification.CertificateChain = [_pki.IntermediateLeafPem, _pki.IntermediatePem, _pki.RootPem];

        var report = VerifyUnder(record, _reader.FromPem([_pki.RootPem]));

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_chain_of_only_the_intermediate_passes()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.LeafCertificate = _pki.IntermediateLeafPem;
        record.Verification.CertificateChain = [_pki.IntermediatePem];

        var report = VerifyUnder(record, _reader.FromPem([_pki.RootPem]));

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_leaf_and_intermediate_chain_without_the_root_passes()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.LeafCertificate = _pki.IntermediateLeafPem;
        record.Verification.CertificateChain = [_pki.IntermediateLeafPem, _pki.IntermediatePem];

        var report = VerifyUnder(record, _reader.FromPem([_pki.RootPem]));

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_leaf_intermediate_root_chain_fails_when_a_different_root_is_pinned()
    {
        var stranger = TestPki.Create("Some Other Root");
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.LeafCertificate = _pki.IntermediateLeafPem;
        record.Verification.CertificateChain = [_pki.IntermediateLeafPem, _pki.IntermediatePem, _pki.RootPem];

        var report = VerifyUnder(record, _reader.FromPem([stranger.RootPem]));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_self_signed_but_unpinned_root_in_the_chain_fails_even_when_the_chain_is_internally_consistent()
    {
        var stranger = TestPki.Create("Some Other Root");
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.LeafCertificate = stranger.IntermediateLeafPem;
        record.Verification.CertificateChain = [stranger.IntermediateLeafPem, stranger.IntermediatePem, stranger.RootPem];

        var report = VerifyUnder(record, _reader.FromPem([_pki.RootPem]));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public void A_signing_time_outside_the_validity_window_fails_the_certificate_chain()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Verification!.SignedAtUtc = new DateTimeOffset(TestPki.NotAfter.AddDays(1));

        var report = VerifyUnder(record, _reader.FromPem([_pki.RootPem]));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "certificateChain"));
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
