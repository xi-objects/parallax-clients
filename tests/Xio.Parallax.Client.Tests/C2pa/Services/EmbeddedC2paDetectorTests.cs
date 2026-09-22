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
        Assert.NotNull(result.Store);
        Assert.Equal(store, result.Store.Bytes.ToArray());
    }

    [Fact]
    public void A_jpeg_missing_one_app11_packet_is_reported_as_malformed()
    {
        var segments = TestCarriers.App11Payloads(TestCarriers.SyntheticStore(), 1, 3);

        var result = _detector.Detect(TestCarriers.Jpeg([segments[0], segments[2]]));

        Assert.Equal(C2paCarrier.Jpeg, result.Carrier);
        Assert.Null(result.Store);
        Assert.Contains("not consecutive", result.Detail);
    }

    [Fact]
    public void A_jpeg_with_no_app11_segment_carries_no_store()
    {
        var result = _detector.Detect(TestCarriers.Jpeg([]));

        Assert.Equal(C2paCarrier.Jpeg, result.Carrier);
        Assert.Null(result.Store);
        Assert.Contains("no JUMBF APP11", result.Detail);
    }

    [Fact]
    public void A_png_cabx_chunk_yields_the_whole_superbox()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.Png(("caBX", store)));

        Assert.Equal(C2paCarrier.Png, result.Carrier);
        Assert.NotNull(result.Store);
        Assert.Equal(store, result.Store.Bytes.ToArray());
    }

    [Fact]
    public void A_png_without_a_cabx_chunk_carries_no_store()
    {
        var result = _detector.Detect(TestCarriers.Png());

        Assert.Equal(C2paCarrier.Png, result.Carrier);
        Assert.Null(result.Store);
        Assert.Contains("no caBX", result.Detail);
    }

    [Fact]
    public void A_png_whose_cabx_is_not_a_jumb_box_is_a_clear_failure()
    {
        var notJumb = TestCarriers.Box("json", Encoding.ASCII.GetBytes("{}"));

        var result = _detector.Detect(TestCarriers.Png(("caBX", notJumb)));

        Assert.Equal(C2paCarrier.Png, result.Carrier);
        Assert.Null(result.Store);
        Assert.Contains("'json' box, not a jumb superbox", result.Detail);
    }

    [Fact]
    public void A_jumb_box_without_the_c2pa_store_uuid_is_a_clear_failure()
    {
        var other = TestCarriers.Box("jumb", TestCarriers.Description(TestCarriers.ManifestUuid, "c2pa"));

        var result = _detector.Detect(TestCarriers.Png(("caBX", other)));

        Assert.Null(result.Store);
        Assert.Contains("C2PA manifest-store UUID", result.Detail);
    }

    [Fact]
    public void A_webp_c2pa_chunk_yields_the_whole_superbox()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.WebP(store));

        Assert.Equal(C2paCarrier.WebP, result.Carrier);
        Assert.NotNull(result.Store);
        Assert.Equal(store, result.Store.Bytes.ToArray());
    }

    [Fact]
    public void A_tiff_tag_52545_yields_the_whole_superbox()
    {
        var store = TestCarriers.SyntheticStore();

        var result = _detector.Detect(TestCarriers.Tiff(store));

        Assert.Equal(C2paCarrier.Tiff, result.Carrier);
        Assert.NotNull(result.Store);
        Assert.Equal(store, result.Store.Bytes.ToArray());
    }

    [Fact]
    public void A_gif_is_unsupported_not_reported_as_carrying_no_c2pa()
    {
        var result = _detector.Detect(TestCarriers.Gif());

        Assert.Equal(C2paCarrier.Unsupported, result.Carrier);
        Assert.Null(result.Store);
        Assert.Contains("not determined", result.Detail);
    }

    [Fact]
    public void The_box_walk_lists_every_box_with_its_label_depth_and_length()
    {
        var store = TestCarriers.SyntheticStore();

        var boxes = _detector.Detect(TestCarriers.Png(("caBX", store))).Store!.Boxes;

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
