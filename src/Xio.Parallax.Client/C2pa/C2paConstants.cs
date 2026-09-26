namespace Xio.Parallax.Client.C2pa;

/// <summary>The carrier signatures, box types, identifiers and manifest kinds the JUMBF and C2PA embedding rules fix.</summary>
internal static class C2paConstants
{
    internal const string SuperboxType = "jumb";

    internal const string DescriptionType = "jumd";

    internal const string C2paKind = "c2pa";

    internal const string JumbfKind = "jumbf";

    internal const string C2paStoreLabel = "c2pa";

    internal const int MaxBoxDepth = 64;

    internal const byte LabelToggle = 0x02;

    internal const int JumdUuidLength = 16;

    internal const string PngStoreChunk = "caBX";

    internal const string PngEndChunk = "IEND";

    internal const string WebPStoreChunk = "C2PA";

    internal const byte JpegMarkerPrefix = 0xFF;

    internal const byte JpegApp11 = 0xEB;

    internal const byte JpegStartOfScan = 0xDA;

    internal const byte JpegEndOfImage = 0xD9;

    internal const ushort TiffStoreTag = 0xCD41;

    internal const ushort TiffUndefinedType = 7;

    internal const int TiffMaxIfds = 64;

    internal static readonly byte[] C2paStoreUuid = Convert.FromHexString("6332706100110010800000AA00389B71");

    internal static readonly byte[] PngSignature = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];

    internal static readonly byte[] JpegSignature = [0xFF, 0xD8, 0xFF];

    internal static readonly byte[] JpegApp11Magic = [0x4A, 0x50];

    internal static readonly byte[] RiffMagic = [0x52, 0x49, 0x46, 0x46];

    internal static readonly byte[] WebPMagic = [0x57, 0x45, 0x42, 0x50];

    internal static readonly byte[] TiffLittleEndian = [0x49, 0x49, 0x2A, 0x00];

    internal static readonly byte[] TiffBigEndian = [0x4D, 0x4D, 0x00, 0x2A];
}
