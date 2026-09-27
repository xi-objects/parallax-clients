namespace Xio.Parallax.Client.Tests.Sequences.Support;

// PC-103: reads a multipart body at byte level, so a binary frame part survives the round trip
/// <summary>One part read back out of a raw multipart/form-data body, its bytes untouched.</summary>
/// <param name="Name">The part's Content-Disposition name.</param>
/// <param name="ContentType">The part's own Content-Type header, or null when it sent none.</param>
/// <param name="Body">The part's raw body bytes, exactly as sent.</param>
internal sealed record RawMultipartPart(string Name, string? ContentType, byte[] Body);

// PC-103: MultipartWireReader reads only headers as text, which corrupts a binary PX frame part;
// this reader keeps every part's body as raw bytes, only decoding its own headers as ASCII
/// <summary>
/// Parses a raw multipart/form-data body into its named parts, keeping each part's body as raw
/// bytes rather than decoded text, so an arbitrary binary payload (a PX frame) survives intact.
/// </summary>
internal static class RawMultipartReader
{
    private static readonly byte[] HeaderBodySeparator = "\r\n\r\n"u8.ToArray();

    /// <summary>Reads every part of a captured multipart/form-data body, in wire order.</summary>
    /// <param name="contentTypeHeader">The request's own Content-Type header, carrying the boundary.</param>
    /// <param name="body">The raw request body bytes.</param>
    /// <returns>Every part's name and raw body bytes, in wire order.</returns>
    internal static IReadOnlyList<RawMultipartPart> Read(string? contentTypeHeader, byte[] body)
    {
        ArgumentException.ThrowIfNullOrEmpty(contentTypeHeader);
        ArgumentNullException.ThrowIfNull(body);
        var boundary = Encoding.ASCII.GetBytes("--" + ExtractBoundary(contentTypeHeader));
        var parts = new List<RawMultipartPart>();
        foreach (var segment in Split(body, boundary))
        {
            var trimmed = TrimCrLf(segment);
            if (trimmed.Length == 0)
            {
                continue;
            }

            var separatorIndex = IndexOf(trimmed, HeaderBodySeparator);
            if (separatorIndex < 0)
            {
                continue;
            }

            var headerText = Encoding.ASCII.GetString(trimmed, 0, separatorIndex);
            var name = ExtractNameParameter(headerText);
            if (name is null)
            {
                continue;
            }

            var contentType = ExtractContentType(headerText);
            var bodyStart = separatorIndex + HeaderBodySeparator.Length;
            var partBody = trimmed[bodyStart..];
            parts.Add(new RawMultipartPart(name, contentType, partBody));
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

    private static IEnumerable<byte[]> Split(byte[] body, byte[] boundary)
    {
        var start = 0;
        while (true)
        {
            var index = IndexOf(body, boundary, start);
            if (index < 0)
            {
                yield break;
            }

            var segmentStart = index + boundary.Length;
            var next = IndexOf(body, boundary, segmentStart);
            var segmentEnd = next < 0 ? body.Length : next;
            yield return body[segmentStart..segmentEnd];
            start = segmentEnd;
        }
    }

    // PC-103: strips exactly one leading and one trailing CRLF (never a loop), so a binary
    // frame body ending in bytes that happen to look like CRLF is never eaten into
    private static byte[] TrimCrLf(byte[] segment)
    {
        var start = 0;
        if (segment.Length >= 2 && segment[0] == (byte)'\r' && segment[1] == (byte)'\n')
        {
            start = 2;
        }

        var end = segment.Length;
        if (end - start >= 2 && segment[end - 2] == (byte)'\r' && segment[end - 1] == (byte)'\n')
        {
            end -= 2;
        }

        return segment[start..end];
    }

    private static int IndexOf(byte[] haystack, byte[] needle, int start = 0)
    {
        if (needle.Length == 0 || start > haystack.Length - needle.Length)
        {
            return -1;
        }

        for (var i = start; i <= haystack.Length - needle.Length; i++)
        {
            var found = true;
            for (var j = 0; j < needle.Length; j++)
            {
                if (haystack[i + j] != needle[j])
                {
                    found = false;
                    break;
                }
            }

            if (found)
            {
                return i;
            }
        }

        return -1;
    }

    private static string? ExtractNameParameter(string headerBlock)
    {
        const string marker = " name=";
        var index = headerBlock.IndexOf(marker, StringComparison.Ordinal);
        if (index < 0)
        {
            return null;
        }

        var start = index + marker.Length;
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

    private static string? ExtractContentType(string headerBlock)
    {
        const string prefix = "Content-Type:";
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
