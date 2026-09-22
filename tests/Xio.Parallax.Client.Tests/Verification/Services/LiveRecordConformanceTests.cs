namespace Xio.Parallax.Client.Tests.Verification.Services;

/// <summary>
/// Conformance tests over one real published record captured from the live API
/// (<c>fixtures/README.md</c>): every performed check must pass under the record's own pinned
/// root, Orbital's <c>pinnedRoots</c> must DER-match that root, a foreign root must fail the
/// chain, and a tampered manifest payload must fail its hash.
/// </summary>
public sealed class LiveRecordConformanceTests
{
    private static readonly string FixturesDirectory = Path.Combine(AppContext.BaseDirectory, "fixtures", "record");

    private readonly IAttributionVerifier _verifier = new AttributionVerifier();
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public async Task The_real_record_passes_every_performed_check_under_its_own_pinned_root()
    {
        var record = await LoadRecordAsync();
        var roots = _reader.FromPemFile(Path.Combine(FixturesDirectory, "root.pem"));

        var report = _verifier.Verify(new XioVerifyRecordRequest(record, await LoadImageBytesAsync(), roots));

        Assert.False(report.AnyFailed);
        string[] mustPass =
        [
            "originalImageHash", "contentHash",
            "manifestHash:c2pa", "manifestSignature:c2pa", "manifestSignature:xi-manifest",
            "collectionSignature", "imageSignature", "leafKeyMatchesPublicKey", "certificateChain",
        ];
        Assert.All(mustPass, name => Assert.Equal(VerificationOutcome.Passed, Outcome(report, name)));
        Assert.Equal(VerificationOutcome.NotRecomputable, Outcome(report, "manifestHash:xi-manifest"));
    }

    [Fact]
    public async Task Orbitals_pinned_root_der_matches_root_pem_and_verifies_the_record()
    {
        var infoJson = await File.ReadAllTextAsync(Path.Combine(FixturesDirectory, "orbital-info.json"));
        using var http = new HttpClient(new VerbatimJsonHandler(infoJson));
        IOrbitalTrustRootSource source = new OrbitalTrustRootSource(http);

        var orbitalRoots = await source.FetchAsync(new Uri("https://orbital.example.test/"), CancellationToken.None);

        Assert.Equal(1, orbitalRoots.Count);
        var pinnedRoot = _reader.FromPemFile(Path.Combine(FixturesDirectory, "root.pem"));
        Assert.Equal(pinnedRoot.Certificates[0].GetEncoded(), orbitalRoots.Certificates[0].GetEncoded());

        var record = await LoadRecordAsync();
        var report = _verifier.Verify(new XioVerifyRecordRequest(record, await LoadImageBytesAsync(), orbitalRoots));

        Assert.Equal(VerificationOutcome.Passed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public async Task A_wrong_pinned_root_fails_the_certificate_chain_on_the_real_record()
    {
        var record = await LoadRecordAsync();
        var wrongRoot = _reader.FromPem([TestPki.Create("Some Other Root").RootPem]);

        var report = _verifier.Verify(new XioVerifyRecordRequest(record, await LoadImageBytesAsync(), wrongRoot));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "certificateChain"));
    }

    [Fact]
    public async Task Flipping_one_byte_of_the_c2pa_payload_fails_its_manifest_hash()
    {
        var record = await LoadRecordAsync();
        var roots = _reader.FromPemFile(Path.Combine(FixturesDirectory, "root.pem"));
        var c2pa = record.Manifests!.Single(manifest => manifest.Type == "c2pa");
        var payloadText = Assert.IsType<UntypedString>(c2pa.Payload).GetValue()!;
        var payload = Convert.FromBase64String(payloadText);
        payload[0] ^= 0x01;
        c2pa.Payload = new UntypedString(Convert.ToBase64String(payload));

        var report = _verifier.Verify(new XioVerifyRecordRequest(record, await LoadImageBytesAsync(), roots));

        Assert.Equal(VerificationOutcome.Failed, Outcome(report, "manifestHash:c2pa"));
    }

    private static async Task<PublishedRecordResponse> LoadRecordAsync()
    {
        var json = await File.ReadAllTextAsync(Path.Combine(FixturesDirectory, "record.json"));
        using var document = JsonDocument.Parse(json);
        IParseNode node = new JsonParseNode(document.RootElement);
        return node.GetObjectValue<PublishedRecordResponse>(PublishedRecordResponse.CreateFromDiscriminatorValue)
            ?? throw new InvalidOperationException("record.json did not parse as a PublishedRecordResponse.");
    }

    private static Task<byte[]> LoadImageBytesAsync()
    {
        return File.ReadAllBytesAsync(Path.Combine(FixturesDirectory, "image.png"));
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
