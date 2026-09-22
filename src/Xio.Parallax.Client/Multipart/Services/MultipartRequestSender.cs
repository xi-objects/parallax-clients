namespace Xio.Parallax.Client.Multipart.Services;

/// <summary>
/// Sends a raw multipart/form-data body through a Kiota request adapter, so the response still
/// goes through the client's authentication, error mapping and deserialization.
/// </summary>
internal static class MultipartRequestSender
{
    /// <summary>
    /// Posts the given multipart body to the given URL template and returns the deserialized
    /// response, or throws the request adapter's mapped failure.
    /// </summary>
    /// <typeparam name="T">The response model to deserialize.</typeparam>
    /// <param name="requestAdapter">The request adapter to send through.</param>
    /// <param name="urlTemplate">The URL template, matching the generated request builder's own.</param>
    /// <param name="pathParameters">The path parameters the template needs, including baseurl.</param>
    /// <param name="content">The multipart body; this method takes ownership and disposes it.</param>
    /// <param name="factory">The factory that deserializes the response model.</param>
    /// <param name="errorMapping">The error factories mapping, matching the endpoint's declared responses.</param>
    /// <param name="cancellationToken">Cancels the send.</param>
    /// <returns>The deserialized response, or null on an empty body.</returns>
    internal static async Task<T?> PostAsync<T>(
        IRequestAdapter requestAdapter,
        string urlTemplate,
        IDictionary<string, object> pathParameters,
        MultipartFormDataContent content,
        ParsableFactory<T> factory,
        Dictionary<string, ParsableFactory<IParsable>> errorMapping,
        CancellationToken cancellationToken)
        where T : IParsable
    {
        ArgumentNullException.ThrowIfNull(requestAdapter);
        ArgumentNullException.ThrowIfNull(content);
        using (content)
        {
            var requestInfo = new RequestInformation(Method.POST, urlTemplate, pathParameters);
            requestInfo.Headers.TryAdd("Accept", "application/json");
            var bodyBytes = await content.ReadAsByteArrayAsync(cancellationToken).ConfigureAwait(false);
            var contentType = content.Headers.ContentType?.ToString() ?? "multipart/form-data";
            using var bodyStream = new MemoryStream(bodyBytes);
            requestInfo.SetStreamContent(bodyStream, contentType);
            return await requestAdapter.SendAsync(requestInfo, factory, errorMapping, cancellationToken).ConfigureAwait(false);
        }
    }
}
