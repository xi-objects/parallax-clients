namespace Xio.Parallax.Client.Tests.C2pa.Services;

public sealed class C2paRecordComparerTests
{
    private static readonly string FixturesDirectory = Path.Combine(AppContext.BaseDirectory, "fixtures", "record");

    private readonly IC2paRecordComparer _comparer = new C2paRecordComparer();
    private readonly TestPki _pki = TestPki.Create();

    [Fact]
    public void A_store_whose_blake3_is_a_jumbf_manifest_hash_matches_that_manifest()
    {
        var comparison = _comparer.Compare(StoreOf(SignedRecordFactory.C2paBytes), SignedRecordFactory.Create(_pki));

        Assert.Equal(C2paComparisonOutcome.Match, comparison.Outcome);
        Assert.Equal("c2pa", comparison.MatchedKind);
    }

    [Fact]
    public void A_store_no_jumbf_manifest_hashes_to_is_a_mismatch()
    {
        var comparison = _comparer.Compare(StoreOf(TestCarriers.SyntheticStore()), SignedRecordFactory.Create(_pki));

        Assert.Equal(C2paComparisonOutcome.Mismatch, comparison.Outcome);
        Assert.Null(comparison.MatchedKind);
    }

    [Fact]
    public void A_record_with_no_jumbf_form_manifest_is_absent_from_record()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Manifests = [.. record.Manifests!.Where(manifest => manifest.Form != PublishedRecordResponse_manifests_form.Jumbf)];

        var comparison = _comparer.Compare(StoreOf(SignedRecordFactory.C2paBytes), record);

        Assert.Equal(C2paComparisonOutcome.AbsentFromRecord, comparison.Outcome);
    }

    [Fact]
    public void A_json_form_manifest_whose_hash_equals_the_store_is_never_compared()
    {
        var record = SignedRecordFactory.Create(_pki);
        var xi = record.Manifests!.Single(manifest => manifest.Form == PublishedRecordResponse_manifests_form.Json);
        xi.Hash = Convert.ToHexStringLower(SignedRecordFactory.Blake3Digest(SignedRecordFactory.XiCarrierBytes));
        record.Manifests = [xi];

        var comparison = _comparer.Compare(StoreOf(SignedRecordFactory.XiCarrierBytes), record);

        Assert.Equal(C2paComparisonOutcome.AbsentFromRecord, comparison.Outcome);
    }

    [Fact]
    public void A_record_that_is_not_published_is_not_published()
    {
        var record = SignedRecordFactory.Create(_pki);
        record.Outcome = PublishedRecordOutcome.TakenDown;

        var comparison = _comparer.Compare(StoreOf(SignedRecordFactory.C2paBytes), record);

        Assert.Equal(C2paComparisonOutcome.NotPublished, comparison.Outcome);
    }

    [Fact]
    public void AsManifestPart_yields_kind_c2pa_form_c2pa_and_the_store_bytes()
    {
        var store = new EmbeddedC2paDetector().Detect(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore()))).Store!;

        var part = C2paAttachment.AsManifestPart(store);

        Assert.Equal("c2pa", part.Kind);
        Assert.Equal(ManifestForm.C2pa, part.Form);
        Assert.Equal(store.Bytes.ToArray(), part.Bytes.ToArray());
    }

    [FixtureFact("record")]
    public async Task The_real_fixture_image_yields_the_c2pa_store_carried_in_its_caBX_chunk()
    {
        var expectedStore = await File.ReadAllBytesAsync(Path.Combine(FixturesDirectory, "manifest.jumbf"));

        var result = new EmbeddedC2paDetector().Detect(await LoadImageBytesAsync());

        Assert.Equal(C2paCarrier.Png, result.Carrier);
        Assert.NotNull(result.Store);
        Assert.Equal(expectedStore, result.Store.Bytes.ToArray());
        JumbfBoxSummary[] expectedBoxes =
        [
            new("jumb", "c2pa", 0, expectedStore.Length),
            new("jumd", "c2pa", 1, 30),
            new("json", null, 1, expectedStore.Length - 38),
        ];
        Assert.Equal(expectedBoxes, result.Store.Boxes);
    }

    [FixtureFact("record")]
    public async Task The_real_fixture_stores_hash_matches_the_real_records_c2pa_manifest()
    {
        var store = await DetectRealStoreAsync();

        var comparison = _comparer.Compare(store, await LoadRecordAsync());

        Assert.Equal(C2paComparisonOutcome.Match, comparison.Outcome);
        Assert.Equal("c2pa", comparison.MatchedKind);
    }

    [FixtureFact("record")]
    public async Task Flipping_one_byte_of_the_real_fixture_store_fails_to_match_the_real_record()
    {
        var store = await DetectRealStoreAsync();
        var tampered = store.Bytes.ToArray();
        tampered[^1] ^= 0x01;

        var comparison = _comparer.Compare(new EmbeddedC2paStore(tampered, store.Boxes), await LoadRecordAsync());

        Assert.Equal(C2paComparisonOutcome.Mismatch, comparison.Outcome);
        Assert.Null(comparison.MatchedKind);
    }

    [FixtureFact("record")]
    public async Task AsManifestPart_carries_the_real_fixture_stores_bytes_unchanged()
    {
        var store = await DetectRealStoreAsync();

        var part = C2paAttachment.AsManifestPart(store);

        Assert.Equal(store.Bytes.ToArray(), part.Bytes.ToArray());
    }

    private static EmbeddedC2paStore StoreOf(byte[] bytes)
    {
        return new EmbeddedC2paStore(bytes, []);
    }

    private static async Task<EmbeddedC2paStore> DetectRealStoreAsync()
    {
        return new EmbeddedC2paDetector().Detect(await LoadImageBytesAsync()).Store
            ?? throw new InvalidOperationException("image.png did not yield an embedded C2PA store.");
    }

    private static Task<byte[]> LoadImageBytesAsync()
    {
        return File.ReadAllBytesAsync(Path.Combine(FixturesDirectory, "image.png"));
    }

    private static async Task<PublishedRecordResponse> LoadRecordAsync()
    {
        var json = await File.ReadAllTextAsync(Path.Combine(FixturesDirectory, "record.json"));
        using var document = JsonDocument.Parse(json);
        IParseNode node = new JsonParseNode(document.RootElement);
        return node.GetObjectValue<PublishedRecordResponse>(PublishedRecordResponse.CreateFromDiscriminatorValue)
            ?? throw new InvalidOperationException("record.json did not parse as a PublishedRecordResponse.");
    }
}
