namespace Xio.Parallax.Client.Tests.Verification.Services;

/// <summary>
/// Conformance test over one real production record registered through the older Forensics Lab
/// path (<c>fixtures/README.md</c>): <c>canonicalVersion: 0</c>, <c>hashAlgorithm: "blake3-256"</c>
/// (lower-case), <c>contentHash</c> in upper-case hex, a single <c>c2pa</c> manifest with
/// <c>hash: null</c> and <c>signature: null</c>, and no <c>collectionSignature</c>. This verifier
/// implements no canonical version 0 preimage, so the manifest and collection checks are never
/// passed; the image signature, leaf key and chain checks are unaffected and must pass.
/// Captured 2026-09-23 from
/// <c>https://<production-forensics-lab-host>/api/attribution/records</c>.
/// The chain ends at <c>CN=Institute of Provenance Root CA</c>, which
/// <c>fixtures/record/orbital-info.json</c>'s dev root does not carry, so the roots here were
/// fetched from production Orbital's own <c>/info</c> instead (<c>fixtures/record-legacy/orbital-info.json</c>).
/// </summary>
public sealed class LegacyRecordConformanceTests
{
    private static readonly string FixturesDirectory = Path.Combine(AppContext.BaseDirectory, "fixtures", "record-legacy");

    private readonly IAttributionVerifier _verifier = new AttributionVerifier();
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public async Task The_legacy_record_verifies_with_every_performed_check_passed_and_manifest_checks_not_recomputable()
    {
        var record = await LoadRecordAsync();
        var roots = _reader.FromPemFile(Path.Combine(FixturesDirectory, "root.pem"));

        var report = _verifier.Verify(new XioVerifyRecordRequest(record, null, roots));

        Assert.False(report.AnyFailed);
        Assert.True(report.AllPerformedPassed);
        string[] mustPass = ["originalImageHash", "imageSignature", "leafKeyMatchesPublicKey", "certificateChain"];
        Assert.All(mustPass, name => Assert.Equal(VerificationOutcome.Passed, Outcome(report, name)));
        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "contentHash"));
        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "manifestHash:c2pa"));
        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "manifestSignature:c2pa"));
        Assert.Equal(VerificationOutcome.NotPerformed, Outcome(report, "collectionSignature"));
    }

    [Fact]
    public async Task Orbitals_pinned_root_der_matches_root_pem_and_verifies_the_legacy_record()
    {
        var infoJson = await File.ReadAllTextAsync(Path.Combine(FixturesDirectory, "orbital-info.json"));
        using var http = new HttpClient(new VerbatimJsonHandler(infoJson));
        IOrbitalTrustRootSource source = new OrbitalTrustRootSource(http);

        var orbitalRoots = await source.FetchAsync(new Uri("https://orbital.example.test/"), CancellationToken.None);

        Assert.Equal(1, orbitalRoots.Count);
        var pinnedRoot = _reader.FromPemFile(Path.Combine(FixturesDirectory, "root.pem"));
        Assert.Equal(pinnedRoot.Certificates[0].GetEncoded(), orbitalRoots.Certificates[0].GetEncoded());

        var record = await LoadRecordAsync();
        var report = _verifier.Verify(new XioVerifyRecordRequest(record, null, orbitalRoots));

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public async Task A_tampered_image_signature_byte_fails_on_the_legacy_record()
    {
        var record = await LoadRecordAsync();
        var roots = _reader.FromPemFile(Path.Combine(FixturesDirectory, "root.pem"));
        var signature = Convert.FromBase64String(record.Verification!.Signature!);
        signature[0] ^= 0x01;
        record.Verification.Signature = Convert.ToBase64String(signature);

        var report = _verifier.Verify(new XioVerifyRecordRequest(record, null, roots));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "imageSignature"));
    }

    private static async Task<PublishedRecordResponse> LoadRecordAsync()
    {
        var json = await File.ReadAllTextAsync(Path.Combine(FixturesDirectory, "record.json"));
        using var document = JsonDocument.Parse(json);
        IParseNode node = new JsonParseNode(document.RootElement);
        return node.GetObjectValue<PublishedRecordResponse>(PublishedRecordResponse.CreateFromDiscriminatorValue)
            ?? throw new InvalidOperationException("record.json did not parse as a PublishedRecordResponse.");
    }

    private static VerificationOutcome Outcome(VerificationReport report, string name)
    {
        var check = report.Find(name);
        Assert.NotNull(check);
        return check.Outcome;
    }

    /// <summary>An HTTP handler that answers every request with the same JSON body, verbatim.</summary>
    private sealed class VerbatimJsonHandler(string _body) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(_body, Encoding.UTF8, "application/json"),
            });
        }
    }
}
