namespace Xio.Parallax.Client.C2pa.Enums;

/// <summary>The carrier format a file was recognised as, by its signature.</summary>
public enum C2paCarrier
{
    /// <summary>A JPEG file; a C2PA store rides in APP11 segments.</summary>
    Jpeg,

    /// <summary>A PNG file; a C2PA store rides in a caBX chunk.</summary>
    Png,

    /// <summary>A WebP file; a C2PA store rides in a RIFF chunk with FourCC C2PA.</summary>
    WebP,

    /// <summary>A TIFF or DNG file; a C2PA store rides in tag 52545 of a top-level IFD.</summary>
    Tiff,

    /// <summary>A file whose signature is not one of the supported carriers; nothing is said about its C2PA content.</summary>
    Unsupported,
}

/// <summary>How an embedded C2PA store compares with a recovered record's manifests.</summary>
public enum C2paComparisonOutcome
{
    /// <summary>The BLAKE3-256 of the store bytes equals the declared hash of one of the record's jumbf-form manifests.</summary>
    Match,

    /// <summary>The record carries at least one jumbf-form manifest, and none declares the store's BLAKE3-256 hash.</summary>
    Mismatch,

    /// <summary>The record carries no jumbf-form manifest.</summary>
    AbsentFromRecord,

    /// <summary>The record's outcome is not published.</summary>
    NotPublished,
}
