namespace Xio.Parallax.Client.Verification.Interfaces;

/// <summary>Decodes the record's hex and base64 fields; every decoder returns null rather than throwing.</summary>
internal interface IVerificationEncoding
{
    /// <summary>Decodes hex text (either case); returns null when the text is absent or not hex.</summary>
    byte[]? TryHex(string? text);

    /// <summary>Decodes standard base64 text; returns null when the text is absent or not base64.</summary>
    byte[]? TryBase64(string? text);

    /// <summary>Decodes base64url text, padded or not, or standard base64 text; returns null when it is neither.</summary>
    byte[]? TryBase64Url(string? text);
}
