namespace Xio.Parallax.Client.Verification.Services;

internal sealed class VerificationEncoding : IVerificationEncoding
{
    public byte[]? TryHex(string? text)
    {
        if (string.IsNullOrEmpty(text) || text.Length % 2 != 0)
        {
            return null;
        }

        try
        {
            return Convert.FromHexString(text);
        }
        catch (FormatException)
        {
            return null;
        }
    }

    public byte[]? TryBase64(string? text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return null;
        }

        try
        {
            return Convert.FromBase64String(text);
        }
        catch (FormatException)
        {
            return null;
        }
    }

    public byte[]? TryBase64Url(string? text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return null;
        }

        var normalized = text
            .Trim()
            .TrimEnd('=')
            .Replace('-', '+')
            .Replace('_', '/');
        var remainder = normalized.Length % 4;
        if (remainder == 1)
        {
            return null;
        }

        if (remainder != 0)
        {
            normalized += new string('=', 4 - remainder);
        }

        return TryBase64(normalized);
    }
}
