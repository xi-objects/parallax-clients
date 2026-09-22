namespace Xio.Parallax.Client.Verification.Models;

/// <summary>Asks for one published record to be verified against pinned roots.</summary>
/// <param name="Record">The record as the API returned it.</param>
/// <param name="OriginalImageBytes">The original image bytes, when the caller has them; without them the two image-hash checks are not performed.</param>
/// <param name="Roots">The pinned roots the certificate chain must reach.</param>
public sealed record XioVerifyRecordRequest(PublishedRecordResponse Record,
                                            ReadOnlyMemory<byte>? OriginalImageBytes,
                                            TrustRoots Roots);

/// <summary>One named check of a published record and its outcome.</summary>
/// <param name="Name">The check's name, for example <c>contentHash</c> or <c>manifestSignature:c2pa</c>.</param>
/// <param name="Outcome">The check's outcome.</param>
/// <param name="Detail">A human-readable account of what was compared and what was found.</param>
public sealed record VerificationCheck(string Name,
                                       VerificationOutcome Outcome,
                                       string Detail);

/// <summary>The per-check verdict of verifying one published record.</summary>
/// <param name="Checks">Every check run, in order.</param>
public sealed record VerificationReport(IReadOnlyList<VerificationCheck> Checks)
{
    /// <summary>Every check run, in order.</summary>
    public IReadOnlyList<VerificationCheck> Checks { get; } = Checks ?? throw new ArgumentNullException(nameof(Checks));

    /// <summary>True only when every check is <see cref="VerificationOutcome.Passed"/>; any <see cref="VerificationOutcome.NotRecomputable"/> or <see cref="VerificationOutcome.NotPerformed"/> check makes it false.</summary>
    public bool AllPassed => Checks.Count > 0 && Checks.All(c => c.Outcome == VerificationOutcome.Passed);

    /// <summary>True when at least one check passed and no check failed; not-recomputable and not-performed checks are excluded, not counted as passed.</summary>
    public bool AllPerformedPassed => Checks.Any(c => c.Outcome == VerificationOutcome.Passed) && !AnyFailed;

    /// <summary>True when any check is <see cref="VerificationOutcome.Failed"/>.</summary>
    public bool AnyFailed => Checks.Any(c => c.Outcome == VerificationOutcome.Failed);

    /// <summary>Returns the check with the given name, or null when no check has that name.</summary>
    public VerificationCheck? Find(string name)
    {
        return Checks.FirstOrDefault(c => string.Equals(c.Name, name, StringComparison.Ordinal));
    }
}
