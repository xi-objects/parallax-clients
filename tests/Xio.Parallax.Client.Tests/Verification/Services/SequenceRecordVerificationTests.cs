namespace Xio.Parallax.Client.Tests.Verification.Services;

// PC-119: a published sequence record verified end to end through AttributionVerifier - the sequence hash recomputed
// from its listed frame hashes, and the summary signature over the version-1 preimage, beside the record's own checks
public sealed class SequenceRecordVerificationTests
{
    private readonly TestPki _pki = TestPki.Create();
    private readonly IAttributionVerifier _verifier = new AttributionVerifier();
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public void A_faithful_sequence_record_passes_its_sequence_hash_and_summary_signature()
    {
        var report = Verify(SignedRecordFactory.CreateSequence(_pki));

        Assert.False(report.AnyFailed);
        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "sequenceHash"));
        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "summarySignature"));
        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "imageSignature"));
        Assert.Equal(["sequenceHash", "summarySignature"], report.Checks.TakeLast(2).Select(c => c.Name));
    }

    [Fact]
    public void An_image_record_carries_no_sequence_checks()
    {
        var report = Verify(SignedRecordFactory.Create(_pki));

        Assert.Null(report.Find("sequenceHash"));
        Assert.Null(report.Find("summarySignature"));
    }

    // PC-119: the summary signature is what binds each frame hash to its frame id and image - swapping either, or the
    // verdict, leaves the frame hashes (so the sequence hash) intact and fails the signature alone
    [Theory]
    [InlineData("image")]
    [InlineData("frameId")]
    [InlineData("reach")]
    [InlineData("expectedSize")]
    public void A_summary_altered_beside_its_frame_hashes_fails_the_signature_alone(string altered)
    {
        var record = SignedRecordFactory.CreateSequence(_pki);
        var sequence = record.Sequence!;
        switch (altered)
        {
            case "image":
                sequence.Frames![0].OriginalImageHash = Convert.ToHexStringLower(SignedRecordFactory.Blake3Digest(Encoding.ASCII.GetBytes("another image")));
                break;
            case "frameId":
                sequence.Frames![0].FrameId = 97;
                break;
            case "reach":
                sequence.Verdict!.Reach = 172_791;
                break;
            case "expectedSize":
                sequence.ExpectedSize = null;
                break;
        }

        var report = Verify(record);

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "sequenceHash"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "summarySignature"));
    }

    [Fact]
    public void A_frame_hash_out_of_place_fails_the_sequence_hash()
    {
        var record = SignedRecordFactory.CreateSequence(_pki);
        var frames = record.Sequence!.Frames!;
        (frames[0], frames[1]) = (frames[1], frames[0]);

        var report = Verify(record);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "sequenceHash"));
        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "summarySignature"));
    }

    [Fact]
    public void A_sequence_committed_before_summary_signing_reports_its_positions_as_not_proven_never_failed()
    {
        var report = Verify(SignedRecordFactory.CreateSequence(_pki, signSummary: false));

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "sequenceHash"));
        var summary = report.Find("summarySignature");
        Assert.NotNull(summary);
        Assert.Equal(VerificationOutcome.NotPerformed, summary.Outcome);
        Assert.Contains("reported, not proven", summary.Detail, StringComparison.Ordinal);
        Assert.False(report.AnyFailed);
    }

    [Fact]
    public void A_signature_without_its_preimage_version_fails()
    {
        var record = SignedRecordFactory.CreateSequence(_pki);
        record.Sequence!.SummaryPreimageVersion = null;

        Assert.Equal(VerificationOutcome.Failed, Outcome(Verify(record), "summarySignature"));
    }

    [Fact]
    public void A_preimage_version_this_verifier_does_not_lay_out_is_refused_by_name()
    {
        var record = SignedRecordFactory.CreateSequence(_pki);
        record.Sequence!.SummaryPreimageVersion = 2;

        var refusal = Assert.Throws<VerificationRefusedException>(() => Verify(record));
        Assert.Contains("summaryPreimageVersion 2", refusal.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_listed_frame_without_a_32_byte_hash_fails_both_checks_naming_it()
    {
        var record = SignedRecordFactory.CreateSequence(_pki);
        record.Sequence!.Frames![2].FrameHash = "abcd";

        var report = Verify(record);

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "sequenceHash"));
        Assert.Contains("Listed frame 2", report.Find("summarySignature")!.Detail, StringComparison.Ordinal);
    }

    private VerificationReport Verify(PublishedRecordResponse record)
    {
        return _verifier.Verify(new XioVerifyRecordRequest(record, null, _reader.FromPem([_pki.RootPem])));
    }

    private static VerificationOutcome Outcome(VerificationReport report, string name)
    {
        var check = report.Find(name);
        Assert.NotNull(check);
        return check.Outcome;
    }
}
