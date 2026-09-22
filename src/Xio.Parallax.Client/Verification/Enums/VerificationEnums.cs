namespace Xio.Parallax.Client.Verification.Enums;

/// <summary>The outcome of one verification check.</summary>
public enum VerificationOutcome
{
    /// <summary>The check was performed and the record's claim held.</summary>
    Passed,

    /// <summary>The check was performed and the record's claim did not hold, or its inputs could not be decoded.</summary>
    Failed,

    /// <summary>The value cannot be recomputed from what the record returns (a JSON-form manifest's stored bytes).</summary>
    NotRecomputable,

    /// <summary>The check needs an input the caller did not supply (the original image bytes).</summary>
    NotPerformed,
}
