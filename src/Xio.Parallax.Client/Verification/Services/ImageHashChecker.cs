namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Checks the record's own <c>originalImageHash</c> against its <c>contentHash</c>, and the original image bytes' BLAKE3-256 against <c>contentHash</c>.</summary>
internal interface IImageHashChecker
{
    /// <summary>Returns the two image-hash checks: <c>originalImageHash</c> is always checked against the record's <c>contentHash</c>; <c>contentHash</c> is not performed when no original bytes are supplied.</summary>
    IReadOnlyList<VerificationCheck> Check(XioImageHashCheckRequest request);
}

internal sealed class ImageHashChecker : IImageHashChecker
{
    private const string NoOriginalBytesDetail = "No original image bytes were supplied.";

    public IReadOnlyList<VerificationCheck> Check(XioImageHashCheckRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var original = CheckOriginalImageHash(request.Record.OriginalImageHash, request.ContentHash.Span);
        if (request.OriginalImageBytes is not { } originalImageBytes)
        {
            return [original, new VerificationCheck(VerificationConstants.ContentHashCheck, VerificationOutcome.NotPerformed, NoOriginalBytesDetail)];
        }

        var blake3 = Blake3Hasher.Hash(originalImageBytes.Span);
        var content = blake3.AsSpan().SequenceEqual(request.ContentHash.Span)
            ? new VerificationCheck(VerificationConstants.ContentHashCheck, VerificationOutcome.Passed, "BLAKE3-256 of the original bytes equals contentHash.")
            : new VerificationCheck(VerificationConstants.ContentHashCheck, VerificationOutcome.Failed, $"BLAKE3-256 of the original bytes is {blake3}; the record's contentHash differs.");
        return [original, content];
    }

    private static VerificationCheck CheckOriginalImageHash(string? declaredOriginalImageHash, ReadOnlySpan<byte> contentHash)
    {
        var contentHashHex = Convert.ToHexStringLower(contentHash);
        return string.Equals(declaredOriginalImageHash, contentHashHex, StringComparison.OrdinalIgnoreCase)
            ? new VerificationCheck(VerificationConstants.OriginalImageHashCheck, VerificationOutcome.Passed, "originalImageHash equals the record's own contentHash.")
            : new VerificationCheck(VerificationConstants.OriginalImageHashCheck, VerificationOutcome.Failed, $"originalImageHash is {declaredOriginalImageHash ?? VerificationConstants.AbsentValue}; the record's contentHash is {contentHashHex}.");
    }
}
