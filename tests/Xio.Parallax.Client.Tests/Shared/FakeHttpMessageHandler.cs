namespace Xio.Parallax.Client.Tests.Shared;

// PC-103: carries the request's own headers too, so a test can assert a header's presence or absence
/// <summary>One outgoing HTTP request captured by <see cref="FakeHttpMessageHandler"/>.</summary>
/// <param name="Method">The HTTP method the request was sent with.</param>
/// <param name="RequestUri">The absolute URI the request was sent to.</param>
/// <param name="ContentType">The request body's Content-Type header, or null when it had no body.</param>
/// <param name="Body">The request body's raw bytes, or an empty array when it had no body.</param>
/// <param name="Headers">The request's own headers (not the content's), by name.</param>
internal sealed record RecordedHttpRequest(HttpMethod Method,
                                            Uri RequestUri,
                                            string? ContentType,
                                            byte[] Body,
                                            IReadOnlyDictionary<string, IEnumerable<string>> Headers);

/// <summary>
/// An <see cref="HttpMessageHandler"/> that records every request it sees and answers with
/// whatever the caller's responder returns, so a <see cref="ParallaxClient"/> under test can be
/// driven against scripted responses without a real server.
/// </summary>
internal sealed class FakeHttpMessageHandler : HttpMessageHandler
{
    private readonly List<RecordedHttpRequest> _requests = [];
    private readonly Func<HttpRequestMessage, HttpResponseMessage> _responder;

    /// <summary>Creates a handler that answers every request with the given responder.</summary>
    /// <param name="responder">Builds the response for a captured request.</param>
    internal FakeHttpMessageHandler(Func<HttpRequestMessage, HttpResponseMessage> responder)
    {
        ArgumentNullException.ThrowIfNull(responder);
        _responder = responder;
    }

    /// <summary>Every request this handler has seen, in the order it saw them.</summary>
    internal IReadOnlyList<RecordedHttpRequest> Requests => _requests;

    // PC-103: also captures the request's own headers, alongside its body
    /// <summary>Records the request's body and headers, then answers it with the responder.</summary>
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var body = request.Content is null
            ? []
            : await request.Content.ReadAsByteArrayAsync(cancellationToken).ConfigureAwait(false);
        var contentType = request.Content?.Headers.ContentType?.ToString();
        var headers = request.Headers.ToDictionary(header => header.Key, header => header.Value, StringComparer.OrdinalIgnoreCase);
        _requests.Add(new RecordedHttpRequest(request.Method, request.RequestUri!, contentType, body, headers));
        return _responder(request);
    }
}
