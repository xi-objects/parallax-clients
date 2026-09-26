namespace Xio.Parallax.Client.Tests.Manifests.Models;

public sealed class SidecarManifestTests
{
    [Fact]
    public void A_json_sidecar_needs_its_kind_stated()
    {
        Assert.Throws<ArgumentException>(() => new SidecarManifest("a.json", ManifestForm.Json, null, new byte[] { 1 }));
    }

    [Fact]
    public void A_json_sidecar_kind_is_validated_by_the_manifest_kind_pattern()
    {
        Assert.Throws<ArgumentException>(() => SidecarManifest.Json("a.json", "has space", new byte[] { 1 }));
    }

    [Fact]
    public void A_jumbf_sidecar_states_no_kind()
    {
        Assert.Throws<ArgumentException>(() => new SidecarManifest("a.jumbf", ManifestForm.Jumbf, "c2pa", new byte[] { 1 }));
    }

    [Fact]
    public void The_c2pa_form_is_a_classification_result_never_an_input()
    {
        Assert.Throws<ArgumentException>(() => new SidecarManifest("a.c2pa", ManifestForm.C2pa, null, new byte[] { 1 }));
    }
}
