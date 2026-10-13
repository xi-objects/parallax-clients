namespace Xio.Parallax.Client.C2pa.Enums;

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
