namespace Xio.Parallax.Client.Tests.Verification.Services;

/// <summary>
/// Conformance test over one real production look-up record (<c>fixtures/README.md</c>): a
/// registration made with no manifests. The record chains to production's
/// <c>CN=Institute of Provenance Root CA</c>, which this repository does not carry, so this test
/// verifies it against the e2e dev root instead. That documents two separate facts: every check
/// that does not depend on the trust root passes, and the certificate chain fails because the
/// dev root is, correctly, the wrong root for a production record.
/// </summary>
public sealed class LookupRecordConformanceTests
{
    private static readonly string LookupDirectory = Path.Combine(AppContext.BaseDirectory, "fixtures", "lookup");
    private static readonly string RecordDirectory = Path.Combine(AppContext.BaseDirectory, "fixtures", "record");

    private readonly IAttributionVerifier _verifier = new AttributionVerifier();
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public async Task A_manifestless_production_record_has_no_collection_to_sign_and_fails_only_the_chain_against_the_dev_root()
    {
        var record = await LoadRecordAsync();
        var devRoot = _reader.FromPemFile(Path.Combine(RecordDirectory, "root.pem"));

        var report = _verifier.Verify(new XioVerifyRecordRequest(record, await LoadImageBytesAsync(), devRoot));

        string[] mustPass = ["originalImageHash", "contentHash", "imageSignature", "leafKeyMatchesPublicKey"];
        Assert.All(mustPass, name => Assert.Equal(VerificationOutcome.Passed, Outcome(report, name)));
        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "collectionSignature"));

        var failed = report.Checks.Where(check => check.Outcome == VerificationOutcome.Failed).Select(check => check.Name);
        Assert.Equal(["certificateChain"], failed);
    }

    private static async Task<PublishedRecordResponse> LoadRecordAsync()
    {
        var json = await File.ReadAllTextAsync(Path.Combine(LookupDirectory, "record.json"));
        using var document = JsonDocument.Parse(json);
        IParseNode node = new JsonParseNode(document.RootElement);
        return node.GetObjectValue<PublishedRecordResponse>(PublishedRecordResponse.CreateFromDiscriminatorValue)
            ?? throw new InvalidOperationException("record.json did not parse as a PublishedRecordResponse.");
    }

    private static Task<byte[]> LoadImageBytesAsync()
    {
        return File.ReadAllBytesAsync(Path.Combine(LookupDirectory, "image.png"));
    }

    private static VerificationOutcome Outcome(VerificationReport report, string name)
    {
        var check = report.Find(name);
        Assert.NotNull(check);
        return check.Outcome;
    }
}
