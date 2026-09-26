namespace Xio.Parallax.Client.C2pa.Enums;

/// <summary>The carrier format a file was recognised as, by its signature.</summary>
public enum C2paCarrier
{
    /// <summary>A JPEG file; JUMBF manifest stores ride in APP11 segments, one or more box instances.</summary>
    Jpeg,

    /// <summary>A PNG file; a JUMBF manifest store rides in a caBX chunk.</summary>
    Png,

    /// <summary>A WebP file; a JUMBF manifest store rides in a RIFF chunk with FourCC C2PA.</summary>
    WebP,

    /// <summary>A TIFF or DNG file; a JUMBF manifest store rides in tag 52545 of a top-level IFD.</summary>
    Tiff,

    /// <summary>A file whose signature is not one of the supported carriers; nothing is said about its embedded manifest content.</summary>
    Unsupported,
}

/// <summary>How an embedded JUMBF manifest store compares with a recovered record's manifests.</summary>
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

/// <summary>What detection found in a file's carrier slot for an embedded JUMBF manifest store.</summary>
public enum EmbeddedC2paOutcome
{
    /// <summary>At least one well-formed store, each classified c2pa or jumbf.</summary>
    Found,

    /// <summary>A supported carrier holding no store.</summary>
    Absent,

    /// <summary>The carrier's slot holds bytes the JUMBF walk refused, or two stores of one kind.</summary>
    Malformed,

    /// <summary>The carrier is not recognised; nothing is said about its content.</summary>
    Unsupported,
}
