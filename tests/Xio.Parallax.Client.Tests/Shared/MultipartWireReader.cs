namespace Xio.Parallax.Client.Tests.Shared;

/// <summary>One named part read back out of a raw multipart/form-data request body.</summary>
/// <param name="Name">The part's Content-Disposition name.</param>
/// <param name="ContentType">The part's own Content-Type header.</param>
internal sealed record MultipartWirePart(string Name, string ContentType);

/// <summary>
/// Parses a raw multipart/form-data request body into its named parts, in wire order, so a test
/// can assert on exactly what was sent rather than on the request-building object model.
/// </summary>
internal static class MultipartWireReader
{
    private const string NameMarker = " name=";
    private const string ContentTypeHeader = "Content-Type:";

    /// <summary>Reads every part of a captured multipart/form-data body, in the order they appear on the wire.</summary>
    /// <param name="contentTypeHeader">The request's own Content-Type header, carrying the boundary.</param>
    /// <param name="body">The raw request body bytes.</param>
    /// <returns>Every part's name and content type, in wire order.</returns>
    internal static IReadOnlyList<MultipartWirePart> Read(string? contentTypeHeader, byte[] body)
    {
        ArgumentException.ThrowIfNullOrEmpty(contentTypeHeader);
        ArgumentNullException.ThrowIfNull(body);
        var boundary = ExtractBoundary(contentTypeHeader);
        var text = Encoding.UTF8.GetString(body);
        var parts = new List<MultipartWirePart>();
        foreach (var segment in text.Split("--" + boundary, StringSplitOptions.None))
        {
            var trimmed = segment.Trim('\r', '\n');
            if (trimmed.Length == 0 || trimmed.StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }

            var headerEnd = trimmed.IndexOf("\r\n\r\n", StringComparison.Ordinal);
            if (headerEnd < 0)
            {
                continue;
            }

            var headerBlock = trimmed[..headerEnd];
            var name = ExtractNameParameter(headerBlock);
            var partContentType = ExtractHeaderLine(headerBlock, ContentTypeHeader);
            if (name is not null && partContentType is not null)
            {
                parts.Add(new MultipartWirePart(name, partContentType));
            }
        }

        return parts;
    }

    private static string ExtractBoundary(string contentTypeHeader)
    {
        const string marker = "boundary=";
        var index = contentTypeHeader.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
        if (index < 0)
        {
            throw new ArgumentException("Content-Type header carries no boundary parameter.", nameof(contentTypeHeader));
        }

        return contentTypeHeader[(index + marker.Length)..].Trim('"');
    }

    /// <summary>
    /// Reads the Content-Disposition "name" parameter, which .NET renders unquoted for a simple
    /// token (name=image) but quoted when the value needs it (name="manifest[c2pa]").
    /// </summary>
    private static string? ExtractNameParameter(string headerBlock)
    {
        var index = headerBlock.IndexOf(NameMarker, StringComparison.Ordinal);
        if (index < 0)
        {
            return null;
        }

        var start = index + NameMarker.Length;
        if (start < headerBlock.Length && headerBlock[start] == '"')
        {
            var quoteStart = start + 1;
            var quoteEnd = headerBlock.IndexOf('"', quoteStart);
            return quoteEnd < 0 ? null : headerBlock[quoteStart..quoteEnd];
        }

        var end = start;
        while (end < headerBlock.Length && headerBlock[end] != ';' && headerBlock[end] != '\r' && headerBlock[end] != '\n')
        {
            end++;
        }

        return headerBlock[start..end];
    }

    private static string? ExtractHeaderLine(string headerBlock, string prefix)
    {
        foreach (var line in headerBlock.Split("\r\n", StringSplitOptions.RemoveEmptyEntries))
        {
            if (line.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                return line[prefix.Length..].Trim();
            }
        }

        return null;
    }
}
