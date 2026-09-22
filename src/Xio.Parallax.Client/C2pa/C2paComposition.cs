namespace Xio.Parallax.Client.C2pa;

/// <summary>The C2PA domain's wiring: each stateless service built once; the public entry points compose from here.</summary>
internal static class C2paComposition
{
    internal static readonly IJumbfStoreReader JumbfReader = new JumbfStoreReader();

    internal static readonly IReadOnlyList<ICarrierReader> CarrierReaders =
    [
        new JpegCarrierReader(JumbfReader),
        new PngCarrierReader(),
        new WebPCarrierReader(),
        new TiffCarrierReader(),
    ];
}
