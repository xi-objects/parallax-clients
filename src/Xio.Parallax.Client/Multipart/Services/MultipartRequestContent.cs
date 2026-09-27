namespace Xio.Parallax.Client.Multipart.Services;

/// <summary>
/// Builds the raw multipart/form-data body for the API's image-and-manifest endpoints, using
/// <see cref="MultipartFormDataContent"/> directly. Kiota's own MultipartBody keys each part by
/// (name, fileName) and silently drops a repeat with the same key; this wire format needs several
/// images to share a manifest kind (manifest[&lt;kind&gt;] is declared as an array of string) and,
/// in a look-up batch, potentially a file name, so parts are appended in order instead of keyed.
/// </summary>
internal static class MultipartRequestContent
{
    private const string ImagePartName = "image";
    private const string ExpectedSizePartName = "expectedSize";
    private const string OctetStreamContentType = "application/octet-stream";

    /// <summary>
    /// Builds the body for an upload that carries images and, for each image, the manifests that
    /// precede it on the wire: POST /registrations and POST /slots/{slotId}/uploads.
    /// </summary>
    /// <param name="images">The images to upload, each with its own manifests, in order.</param>
    /// <returns>A multipart body ready to send.</returns>
    internal static MultipartFormDataContent CreateForUpload(IReadOnlyList<ManifestedImage> images)
    {
        ArgumentNullException.ThrowIfNull(images);
        var content = new MultipartFormDataContent();
        foreach (var entry in images)
        {
            foreach (var manifest in entry.Manifests)
            {
                content.Add(CreatePart(manifest.Bytes, manifest.Form.ToContentType()), $"manifest[{manifest.Kind}]");
            }

            content.Add(CreatePart(entry.Image.Bytes, entry.Image.ContentType), ImagePartName, entry.Image.FileName);
        }

        return content;
    }

    /// <summary>
    /// Builds the body for a look-up upload that carries images only, with no manifests:
    /// POST /lookup and POST /lookup/slots/{lookupSlotId}/queries.
    /// </summary>
    /// <param name="images">The images to look up, in order.</param>
    /// <returns>A multipart body ready to send.</returns>
    internal static MultipartFormDataContent CreateForLookup(IReadOnlyList<ImageUpload> images)
    {
        ArgumentNullException.ThrowIfNull(images);
        var content = new MultipartFormDataContent();
        foreach (var image in images)
        {
            content.Add(CreatePart(image.Bytes, image.ContentType), ImagePartName, image.FileName);
        }

        return content;
    }

    // PC-103: sequence open's manifest[<kind>] parts, no image, plus an optional expectedSize text part
    /// <summary>
    /// Builds the body for opening a sequence, with no image: POST /sequences. Carries every
    /// manifest as a manifest[&lt;kind&gt;] part, then, only when given, the advisory expected
    /// size as a plain text part.
    /// </summary>
    /// <param name="manifests">The manifests to send with open, in the order the wire carries them.</param>
    /// <param name="expectedSize">The sequence's advisory expected size, sent as a text part when given.</param>
    /// <returns>A multipart body ready to send.</returns>
    internal static MultipartFormDataContent CreateForSequenceOpen(IReadOnlyList<ManifestPart> manifests, long? expectedSize)
    {
        ArgumentNullException.ThrowIfNull(manifests);
        var content = new MultipartFormDataContent();
        foreach (var manifest in manifests)
        {
            content.Add(CreatePart(manifest.Bytes, manifest.Form.ToContentType()), $"manifest[{manifest.Kind}]");
        }

        if (expectedSize is { } size)
        {
            content.Add(new StringContent(size.ToString(CultureInfo.InvariantCulture)), ExpectedSizePartName);
        }

        return content;
    }

    // PC-103: one octet-stream file part per frame, named and file-named after its frame id, in upload order
    /// <summary>
    /// Builds the body for uploading sequence frames: POST /sequences/{id}/frames. One
    /// application/octet-stream file part per frame, its part name the frame's own id and its file
    /// name <c>&lt;frameId&gt;.px</c>, in the order given; the server reads only file parts.
    /// </summary>
    /// <param name="frames">The encoded frames to upload, in order.</param>
    /// <returns>A multipart body ready to send.</returns>
    internal static MultipartFormDataContent CreateForSequenceFrames(IReadOnlyList<EncodedFrame> frames)
    {
        ArgumentNullException.ThrowIfNull(frames);
        var content = new MultipartFormDataContent();
        foreach (var frame in frames)
        {
            var frameId = frame.FrameId.ToString(CultureInfo.InvariantCulture);
            var part = new ReadOnlyMemoryContent(frame.Bytes);
            part.Headers.ContentType = MediaTypeHeaderValue.Parse(OctetStreamContentType);
            content.Add(part, frameId, $"{frameId}.px");
        }

        return content;
    }

    // PC-104: the exact byte length of the frames body CreateForSequenceFrames builds, read from the built content itself
    /// <summary>
    /// The byte length of the whole multipart body <see cref="CreateForSequenceFrames"/> builds for
    /// <paramref name="frames"/>: every part's bytes, part headers, boundaries and CRLFs, and the
    /// closing delimiter, as the built content computes it.
    /// </summary>
    /// <param name="frames">The encoded frames the body would carry, in order.</param>
    /// <returns>The body's exact length in bytes.</returns>
    internal static long MeasureSequenceFrames(IReadOnlyList<EncodedFrame> frames)
    {
        using var content = CreateForSequenceFrames(frames);
        return content.Headers.ContentLength
            ?? throw new InvalidOperationException("a sequence frames body could not compute its own length.");
    }

    private static ByteArrayContent CreatePart(ReadOnlyMemory<byte> bytes, string contentType)
    {
        var part = new ByteArrayContent(bytes.ToArray());
        part.Headers.ContentType = MediaTypeHeaderValue.Parse(contentType);
        return part;
    }
}
