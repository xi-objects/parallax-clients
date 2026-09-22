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

    private static ByteArrayContent CreatePart(ReadOnlyMemory<byte> bytes, string contentType)
    {
        var part = new ByteArrayContent(bytes.ToArray());
        part.Headers.ContentType = MediaTypeHeaderValue.Parse(contentType);
        return part;
    }
}
