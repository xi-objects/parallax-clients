namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Checks the original image bytes against the record's SHA-256 <c>originalImageHash</c> and BLAKE3-256 <c>contentHash</c>.</summary>
internal interface IImageHashChecker
{
    /// <summary>Returns the two image-hash checks, both not performed when no original bytes are supplied.</summary>
    IReadOnlyList<VerificationCheck> Check(XioImageHashCheckRequest request);
}

internal sealed class ImageHashChecker : IImageHashChecker
{
    private const string NoOriginalBytesDetail = "No original image bytes were supplied.";

    public IReadOnlyList<VerificationCheck> Check(XioImageHashCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.OriginalImageBytes is not { } originalImageBytes)
        {
            return
            [
                new VerificationCheck(VerificationConstants.OriginalImageHashCheck, VerificationOutcome.NotPerformed, NoOriginalBytesDetail),
                new VerificationCheck(VerificationConstants.ContentHashCheck, VerificationOutcome.NotPerformed, NoOriginalBytesDetail),
            ];
        }

        var bytes = originalImageBytes.Span;
        var declaredSha256 = request.Record.OriginalImageHash;
        var sha256 = Convert.ToHexStringLower(SHA256.HashData(bytes));
        var original = string.Equals(sha256, declaredSha256, StringComparison.OrdinalIgnoreCase)
            ? new VerificationCheck(VerificationConstants.OriginalImageHashCheck, VerificationOutcome.Passed, "SHA-256 of the original bytes equals originalImageHash.")
            : new VerificationCheck(VerificationConstants.OriginalImageHashCheck, VerificationOutcome.Failed, $"SHA-256 of the original bytes is {sha256}; the record says {declaredSha256 ?? VerificationConstants.AbsentValue}.");

        var blake3 = Blake3Hasher.Hash(bytes);
        var content = blake3.AsSpan().SequenceEqual(request.ContentHash.Span)
            ? new VerificationCheck(VerificationConstants.ContentHashCheck, VerificationOutcome.Passed, "BLAKE3-256 of the original bytes equals contentHash.")
            : new VerificationCheck(VerificationConstants.ContentHashCheck, VerificationOutcome.Failed, $"BLAKE3-256 of the original bytes is {blake3}; the record's contentHash differs.");
        return [original, content];
    }
}
