namespace Xio.Parallax.Client.C2pa;

/// <summary>The C2PA domain's wiring: embedded JUMBF detection, the JUMBF walk and the manifest merge, composed once from Xio.Parallax.Manifests.</summary>
internal static class C2paComposition
{
    private static readonly ServiceProvider Provider = new ServiceCollection().AddXioParallaxManifests().BuildServiceProvider();

    internal static readonly IJumbfStoreReader JumbfReader = Provider.GetRequiredService<IJumbfStoreReader>();

    internal static readonly IManifestMerger Merger = Provider.GetRequiredService<IManifestMerger>();
}
