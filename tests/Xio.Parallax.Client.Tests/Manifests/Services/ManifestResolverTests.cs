namespace Xio.Parallax.Client.Tests.Manifests.Services;

public sealed class ManifestResolverTests
{
    private static readonly byte[] Json = "{\"a\":1}"u8.ToArray();

    private readonly ManifestResolver _resolver = new();

    [Fact]
    public void None_yields_no_parts_without_looking_at_the_carrier()
    {
        var parts = _resolver.Resolve(Image(TestCarriers.Gif()), ManifestSelection.None);

        Assert.Empty(parts);
    }

    [Fact]
    public void An_embedded_store_found_is_included_under_its_classified_kind()
    {
        var store = TestCarriers.SyntheticStore();

        var part = Assert.Single(_resolver.Resolve(Image(TestCarriers.Png(("caBX", store))), Embedded()));

        Assert.Equal(("c2pa", ManifestForm.C2pa), (part.Kind, part.Form));
        Assert.Equal(store, part.Bytes.ToArray());
    }

    [Fact]
    public void An_absent_embedded_store_contributes_nothing()
    {
        Assert.Empty(_resolver.Resolve(Image(TestCarriers.Png()), Embedded()));
    }

    [Fact]
    public void A_malformed_embedded_store_refuses()
    {
        var notJumb = TestCarriers.Box("json", Json);

        var refusal = Refused(Image(TestCarriers.Png(("caBX", notJumb))), Embedded());

        Assert.Contains("malformed", refusal.Reason);
    }

    [Fact]
    public void Sidecars_alone_never_look_at_the_embedding()
    {
        var notJumb = TestCarriers.Box("json", Json);

        var part = Assert.Single(_resolver.Resolve(Image(TestCarriers.Png(("caBX", notJumb))), Sidecars(SidecarManifest.Jumbf("a.png.c2pa", TestCarriers.SyntheticStore()))));

        Assert.Equal(("c2pa", ManifestForm.C2pa), (part.Kind, part.Form));
    }

    [Fact]
    public void An_image_whose_format_has_no_jumbf_embedding_keeps_its_sidecars()
    {
        var sidecar = SidecarManifest.Json("a.bmp.json", "xi-manifest", Json);

        var part = Assert.Single(_resolver.Resolve(Image("BM"u8.ToArray(), "a.bmp"), Embedded(sidecar)));

        Assert.Equal("xi-manifest", part.Kind);
    }

    [Fact]
    public void A_json_sidecar_and_an_embedded_store_coexist()
    {
        var image = Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())));

        var parts = _resolver.Resolve(image, Embedded(SidecarManifest.Json("a.png.json", "xi-manifest", Json)));

        Assert.Equal([("xi-manifest", ManifestForm.Json), ("c2pa", ManifestForm.C2pa)], parts.Select(part => (part.Kind, part.Form)));
    }

    [Fact]
    public void Sidecars_go_first_in_the_given_order_then_embedded_stores_in_document_order()
    {
        var other = TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi");
        var jpeg = TestCarriers.Jpeg([.. TestCarriers.App11Payloads(other, 5, 1), .. TestCarriers.App11Payloads(TestCarriers.SyntheticStore(), 1, 1)]);
        var selection = Embedded(SidecarManifest.Json("b.json", "b-kind", Json), SidecarManifest.Json("a.json", "a-kind", Json));

        var parts = _resolver.Resolve(Image(jpeg), selection);

        Assert.Equal(["b-kind", "a-kind", "jumbf", "c2pa"], parts.Select(part => part.Kind));
    }

    [Fact]
    public void A_jumbf_sidecar_byte_identical_to_the_embedded_store_is_included_once()
    {
        var store = TestCarriers.SyntheticStore();

        var parts = _resolver.Resolve(Image(TestCarriers.Png(("caBX", store))), Embedded(SidecarManifest.Jumbf("a.png.c2pa", store)));

        Assert.Equal(("c2pa", ManifestForm.C2pa), (Assert.Single(parts).Kind, parts[0].Form));
    }

    [Fact]
    public void Two_byte_identical_jumbf_sidecars_go_on_the_wire_once()
    {
        var store = TestCarriers.SyntheticStore();

        var parts = _resolver.Resolve(Image(TestCarriers.Png()), Sidecars(SidecarManifest.Jumbf("a.png.c2pa", store), SidecarManifest.Jumbf("a.png.jumbf", store)));

        Assert.Equal("c2pa", Assert.Single(parts).Kind);
    }

    [Fact]
    public void An_embedded_plain_jumbf_store_is_added_beside_a_c2pa_sidecar()
    {
        var plain = TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi");

        var parts = _resolver.Resolve(Image(TestCarriers.Png(("caBX", plain))), Embedded(SidecarManifest.Jumbf("a.png.c2pa", TestCarriers.SyntheticStore())));

        Assert.Equal([("c2pa", ManifestForm.C2pa), ("jumbf", ManifestForm.Jumbf)], parts.Select(part => (part.Kind, part.Form)));
        Assert.Equal(plain, parts[1].Bytes.ToArray());
    }

    [Fact]
    public void Distinct_plain_jumbf_stores_are_all_included()
    {
        var first = TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi");
        var second = TestCarriers.OtherStore(TestCarriers.ClaimUuid, "other");
        var jpeg = TestCarriers.Jpeg([.. TestCarriers.App11Payloads(first, 5, 1), .. TestCarriers.App11Payloads(second, 6, 1)]);

        var parts = _resolver.Resolve(Image(jpeg), Embedded(SidecarManifest.Jumbf("a.png.jumbf", first)));

        Assert.Equal([first, second], parts.Select(part => part.Bytes.ToArray()));
    }

    [Fact]
    public void A_second_distinct_c2pa_manifest_embedded_beside_a_c2pa_sidecar_is_a_conflict()
    {
        var image = Image(TestCarriers.Png(("caBX", TestCarriers.OtherStore(TestCarriers.StoreUuid, "c2pa"))));

        var refusal = Refused(image, Embedded(SidecarManifest.Jumbf("a.png.c2pa", TestCarriers.SyntheticStore())));

        Assert.Contains("conflict", refusal.Reason);
    }

    [Fact]
    public void Two_distinct_c2pa_sidecars_refuse()
    {
        var selection = Sidecars(SidecarManifest.Jumbf("a.c2pa", TestCarriers.SyntheticStore()), SidecarManifest.Jumbf("b.c2pa", TestCarriers.OtherStore(TestCarriers.StoreUuid, "c2pa")));

        var refusal = Refused(Image(TestCarriers.Png()), selection);

        Assert.Contains("2 distinct C2PA manifests", refusal.Reason);
    }

    [Fact]
    public void A_jumbf_sidecar_beside_a_carrier_holding_no_store_is_included_alone_under_its_classified_kind()
    {
        var sidecar = SidecarManifest.Jumbf("a.png.jumbf", TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi"));

        var part = Assert.Single(_resolver.Resolve(Image(TestCarriers.Png()), Sidecars(sidecar)));

        Assert.Equal(("jumbf", ManifestForm.Jumbf), (part.Kind, part.Form));
    }

    [Fact]
    public void A_malformed_jumbf_sidecar_refuses_naming_it()
    {
        var refusal = Refused(Image(TestCarriers.Png()), Sidecars(SidecarManifest.Jumbf("a.png.jumbf", TestCarriers.Box("json", Json))));

        Assert.Contains("'a.png.jumbf' is malformed", refusal.Reason);
    }

    [Fact]
    public void Two_json_manifests_of_one_kind_refuse()
    {
        var selection = Sidecars(SidecarManifest.Json("a.json", "xi-manifest", Json), SidecarManifest.Json("b.json", "xi-manifest", "{}"u8.ToArray()));

        var refusal = Refused(Image(TestCarriers.Png()), selection);

        Assert.Contains("2 JSON manifests of kind 'xi-manifest'", refusal.Reason);
    }

    [Fact]
    public void A_collection_with_two_bad_items_refuses_listing_both_and_returns_nothing()
    {
        ManifestRequest[] requests =
        [
            new(Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())), "first.png"), Embedded(SidecarManifest.Jumbf("first.c2pa", TestCarriers.OtherStore(TestCarriers.StoreUuid, "c2pa")))),
            new(Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())), "good.png"), Embedded()),
            new(Image(TestCarriers.Png(("caBX", TestCarriers.Box("json", Json))), "third.png"), Embedded()),
        ];

        var exception = Assert.Throws<ManifestRefusalException>(() => _resolver.Resolve(requests));

        Assert.Equal(["first.png", "third.png"], exception.Refusals.Select(refusal => refusal.FileName));
        Assert.StartsWith("Manifest resolution refused 2 image(s):", exception.Message);
        Assert.Contains("\nthird.png: ", exception.Message);
    }

    [Fact]
    public void A_collection_resolves_to_one_registration_item_per_request_in_order()
    {
        ManifestRequest[] requests =
        [
            new(Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())), "one.png"), Embedded()),
            new(Image(TestCarriers.Gif(), "two.gif"), ManifestSelection.None),
        ];

        var items = _resolver.Resolve(requests);

        Assert.Equal(["one.png", "two.gif"], items.Select(item => item.Image.FileName));
        Assert.Equal([1, 0], items.Select(item => item.Manifests.Count));
    }

    private static ImageUpload Image(byte[] bytes, string fileName = "a.png")
    {
        return new ImageUpload(fileName, "application/octet-stream", bytes);
    }

    private static ManifestSelection Embedded(params SidecarManifest[] sidecars)
    {
        return new ManifestSelection(true, sidecars);
    }

    private static ManifestSelection Sidecars(params SidecarManifest[] sidecars)
    {
        return new ManifestSelection(false, sidecars);
    }

    private ManifestRefusal Refused(ImageUpload image, ManifestSelection selection)
    {
        var exception = Assert.Throws<ManifestRefusalException>(() => _resolver.Resolve(image, selection));
        var refusal = Assert.Single(exception.Refusals);
        Assert.Equal(image.FileName, refusal.FileName);
        return refusal;
    }
}
