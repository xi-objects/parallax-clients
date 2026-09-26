namespace Xio.Parallax.Client.Tests.C2pa.Services;

public sealed class EmbeddedC2paDetectorTests
{
    private readonly IEmbeddedC2paDetector _detector = new EmbeddedC2paDetector();

    [Fact]
    public void A_jpeg_store_split_across_three_out_of_order_app11_segments_is_reassembled()
    {
        var store = TestCarriers.SyntheticStore();
        var segments = TestCarriers.App11Payloads(store, 7, 3);
        var file = TestCarriers.Jpeg([segments[2], segments[0], segments[1]]);

        var result = _detector.Detect(file);

        Assert.Equal(C2paCarrier.Jpeg, result.Carrier);
        Assert.Equal(EmbeddedC2paOutcome.Found, result.Outcome);
        Assert.Equal(store, Assert.Single(result.Stores).Bytes.ToArray());
    }

    [Fact]
    public void A_jpeg_missing_one_app11_packet_is_malformed()
    {
        var segments = TestCarriers.App11Payloads(TestCarriers.SyntheticStore(), 1, 3);

        var result = _detector.Detect(TestCarriers.Jpeg([segments[0], segments[2]]));

        Assert.Equal(EmbeddedC2paOutcome.Malformed, result.Outcome);
        Assert.Empty(result.Stores);
        Assert.Contains("not consecutive", result.Detail);
    }

    [Fact]
    public void A_jpeg_with_no_app11_segment_is_absent()
    {
        var result = _detector.Detect(TestCarriers.Jpeg([]));

        Assert.Equal(C2paCarrier.Jpeg, result.Carrier);
        Assert.Equal(EmbeddedC2paOutcome.Absent, result.Outcome);
        Assert.Empty(result.Stores);
    }

    [Fact]
    public void A_jpeg_with_two_instances_of_different_kinds_yields_both_stores_in_document_order()
    {
        var other = TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi");
        var c2pa = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.Jpeg([.. TestCarriers.App11Payloads(other, 9, 1), .. TestCarriers.App11Payloads(c2pa, 2, 2)]));

        Assert.Equal(EmbeddedC2paOutcome.Found, result.Outcome);
        Assert.Equal(["jumbf", "c2pa"], result.Stores.Select(store => store.Kind));
        Assert.Equal(other, result.Stores[0].Bytes.ToArray());
        Assert.Equal(c2pa, result.Stores[1].Bytes.ToArray());
    }

    [Fact]
    public void A_jpeg_with_two_instances_of_one_kind_is_malformed_naming_the_count()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.Jpeg([.. TestCarriers.App11Payloads(store, 1, 1), .. TestCarriers.App11Payloads(store, 2, 1)]));

        Assert.Equal(EmbeddedC2paOutcome.Malformed, result.Outcome);
        Assert.Empty(result.Stores);
        Assert.Contains("2 manifest stores of kind 'c2pa'", result.Detail);
    }

    [Fact]
    public void A_jpeg_with_one_malformed_instance_beside_a_well_formed_one_is_malformed()
    {
        var malformed = TestCarriers.Box("jumb", TestCarriers.Box("json", "{}"u8.ToArray()));

        var result = _detector.Detect(TestCarriers.Jpeg([.. TestCarriers.App11Payloads(TestCarriers.SyntheticStore(), 1, 1), .. TestCarriers.App11Payloads(malformed, 2, 1)]));

        Assert.Equal(EmbeddedC2paOutcome.Malformed, result.Outcome);
        Assert.Empty(result.Stores);
    }

    [Fact]
    public void A_jpeg_app11_instance_that_is_not_a_jumb_box_is_ignored()
    {
        var lchk = TestCarriers.Box("LCHK", [0x00, 0x01, 0x02, 0x03]);

        var result = _detector.Detect(TestCarriers.Jpeg([.. TestCarriers.App11Payloads(lchk, 3, 1), .. TestCarriers.App11Payloads(TestCarriers.SyntheticStore(), 1, 1)]));

        Assert.Equal(EmbeddedC2paOutcome.Found, result.Outcome);
        Assert.Equal("c2pa", Assert.Single(result.Stores).Kind);
    }

    [Fact]
    public void A_png_cabx_chunk_yields_the_whole_superbox()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.Png(("caBX", store)));

        Assert.Equal(C2paCarrier.Png, result.Carrier);
        Assert.Equal(store, Assert.Single(result.Stores).Bytes.ToArray());
    }

    [Fact]
    public void A_png_without_a_cabx_chunk_is_absent()
    {
        var result = _detector.Detect(TestCarriers.Png());

        Assert.Equal(EmbeddedC2paOutcome.Absent, result.Outcome);
        Assert.Contains("no caBX", result.Detail);
    }

    [Fact]
    public void A_png_whose_cabx_is_not_a_jumb_box_is_malformed()
    {
        var notJumb = TestCarriers.Box("json", Encoding.ASCII.GetBytes("{}"));

        var result = _detector.Detect(TestCarriers.Png(("caBX", notJumb)));

        Assert.Equal(EmbeddedC2paOutcome.Malformed, result.Outcome);
        Assert.Empty(result.Stores);
        Assert.Contains("'json' box, not a jumb superbox", result.Detail);
    }

    [Theory]
    [InlineData("6332706100110010800000AA00389B71", "c2pa", "c2pa")]
    [InlineData("63326D6100110010800000AA00389B71", "c2pa", "jumbf")]
    [InlineData("6332706100110010800000AA00389B71", "other", "jumbf")]
    public void A_superbox_is_c2pa_only_with_the_store_uuid_and_label_c2pa_else_jumbf(string uuid, string label, string kind)
    {
        var superbox = TestCarriers.OtherStore(Convert.FromHexString(uuid), label);

        var result = _detector.Detect(TestCarriers.Png(("caBX", superbox)));

        Assert.Equal(EmbeddedC2paOutcome.Found, result.Outcome);
        Assert.Equal(kind, Assert.Single(result.Stores).Kind);
    }

    [Fact]
    public void A_webp_c2pa_chunk_yields_the_whole_superbox()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.WebP(store));

        Assert.Equal(C2paCarrier.WebP, result.Carrier);
        Assert.Equal(store, Assert.Single(result.Stores).Bytes.ToArray());
    }

    [Fact]
    public void A_tiff_tag_52545_yields_the_whole_superbox()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.Tiff(store));

        Assert.Equal(C2paCarrier.Tiff, result.Carrier);
        Assert.Equal(store, Assert.Single(result.Stores).Bytes.ToArray());
    }

    [Fact]
    public void A_gif_is_unsupported_not_reported_as_absent()
    {
        var result = _detector.Detect(TestCarriers.Gif());

        Assert.Equal(C2paCarrier.Unsupported, result.Carrier);
        Assert.Equal(EmbeddedC2paOutcome.Unsupported, result.Outcome);
        Assert.Empty(result.Stores);
        Assert.Contains("not determined", result.Detail);
    }

    [Fact]
    public void The_box_walk_lists_every_box_with_its_label_depth_and_length()
    {
        var store = TestCarriers.SyntheticStore();

        var boxes = _detector.Detect(TestCarriers.Png(("caBX", store))).Stores.Single().Boxes;

        JumbfBoxSummary[] expected =
        [
            new("jumb", "c2pa", 0, store.Length),
            new("jumd", "c2pa", 1, 30),
            new("jumb", "urn:uuid:test-manifest", 1, store.Length - 30 - 8),
            new("jumd", "urn:uuid:test-manifest", 2, 48),
            new("jumb", "c2pa.claim", 2, 8 + 36 + 12),
            new("jumd", "c2pa.claim", 3, 36),
            new("cbor", null, 3, 12),
        ];
        Assert.Equal(expected, boxes);
    }
}
