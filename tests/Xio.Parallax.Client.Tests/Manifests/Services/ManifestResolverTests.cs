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
    public void A_malformed_embedded_store_refuses_when_only_a_jumbf_sidecar_is_given()
    {
        var notJumb = TestCarriers.Box("json", Json);

        var refusal = Refused(Image(TestCarriers.Png(("caBX", notJumb))), Sidecars(SidecarManifest.Jumbf("a.png.c2pa", TestCarriers.SyntheticStore())));

        Assert.Contains("malformed", refusal.Reason);
    }

    [Fact]
    public void An_unsupported_carrier_refuses_when_the_embedded_store_is_included()
    {
        var refusal = Refused(Image(TestCarriers.Gif()), Embedded());

        Assert.Contains("not recognised", refusal.Reason);
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
    public void A_jumbf_sidecar_differing_from_the_embedded_store_refuses()
    {
        var image = Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())));
        var sidecar = SidecarManifest.Jumbf("a.png.jumbf", TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi"));

        var refusal = Refused(image, Sidecars(sidecar));

        Assert.Contains("differs from its JUMBF sidecar", refusal.Reason);
    }

    [Fact]
    public void A_jumbf_sidecar_matching_no_embedded_store_refuses_even_when_another_sidecar_matches()
    {
        var store = TestCarriers.SyntheticStore();
        var selection = Sidecars(SidecarManifest.Jumbf("a.png.c2pa", store), SidecarManifest.Jumbf("a.png.jumbf", TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi")));

        var refusal = Refused(Image(TestCarriers.Png(("caBX", store))), selection);

        Assert.Contains("'a.png.jumbf' matches no embedded manifest store", refusal.Reason);
    }

    [Fact]
    public void A_jumbf_sidecar_beside_a_carrier_holding_no_store_is_included_alone_under_its_classified_kind()
    {
        var sidecar = SidecarManifest.Jumbf("a.png.jumbf", TestCarriers.OtherStore(TestCarriers.ManifestUuid, "xi"));

        var part = Assert.Single(_resolver.Resolve(Image(TestCarriers.Png()), Sidecars(sidecar)));

        Assert.Equal(("jumbf", ManifestForm.Jumbf), (part.Kind, part.Form));
    }

    [Fact]
    public void A_jumbf_sidecar_beside_an_unsupported_carrier_refuses()
    {
        var refusal = Refused(Image(TestCarriers.Gif()), Sidecars(SidecarManifest.Jumbf("a.gif.c2pa", TestCarriers.SyntheticStore())));

        Assert.Contains("not recognised", refusal.Reason);
    }

    [Fact]
    public void A_malformed_jumbf_sidecar_refuses_naming_it()
    {
        var refusal = Refused(Image(TestCarriers.Png()), Sidecars(SidecarManifest.Jumbf("a.png.jumbf", TestCarriers.Box("json", Json))));

        Assert.Contains("'a.png.jumbf' is malformed", refusal.Reason);
    }

    [Fact]
    public void Two_manifests_of_one_kind_across_sidecars_and_embedded_stores_refuse()
    {
        var image = Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())));

        var refusal = Refused(image, Embedded(SidecarManifest.Json("a.png.json", "c2pa", Json)));

        Assert.Contains("2 manifests of kind 'c2pa'", refusal.Reason);
    }

    [Fact]
    public void A_collection_with_two_bad_items_refuses_listing_both_and_returns_nothing()
    {
        ManifestRequest[] requests =
        [
            new(Image(TestCarriers.Gif(), "first.gif"), Embedded()),
            new(Image(TestCarriers.Png(("caBX", TestCarriers.SyntheticStore())), "good.png"), Embedded()),
            new(Image(TestCarriers.Png(("caBX", TestCarriers.Box("json", Json))), "third.png"), Embedded()),
        ];

        var exception = Assert.Throws<ManifestRefusalException>(() => _resolver.Resolve(requests));

        Assert.Equal(["first.gif", "third.png"], exception.Refusals.Select(refusal => refusal.FileName));
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
