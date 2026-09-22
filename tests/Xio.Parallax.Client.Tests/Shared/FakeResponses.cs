namespace Xio.Parallax.Client.Tests.Shared;

/// <summary>Builds the canned <see cref="HttpResponseMessage"/> values the fake server scripts.</summary>
internal static class FakeResponses
{
    /// <summary>Builds a successful application/json response.</summary>
    /// <param name="statusCode">The status code to answer with.</param>
    /// <param name="json">The response body.</param>
    /// <returns>A response carrying the given body as application/json.</returns>
    internal static HttpResponseMessage Json(HttpStatusCode statusCode, string json)
    {
        return new HttpResponseMessage(statusCode)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json"),
        };
    }

    /// <summary>Builds an application/problem+json refusal, optionally carrying a Retry-After header.</summary>
    /// <param name="statusCode">The status code to refuse with.</param>
    /// <param name="json">The problem+json body.</param>
    /// <param name="retryAfter">The Retry-After delay to send, when the refusal carries one.</param>
    /// <returns>A response carrying the given problem body as application/problem+json.</returns>
    internal static HttpResponseMessage Problem(HttpStatusCode statusCode, string json, TimeSpan? retryAfter = null)
    {
        var response = new HttpResponseMessage(statusCode)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/problem+json"),
        };
        if (retryAfter is { } delay)
        {
            response.Headers.RetryAfter = new RetryConditionHeaderValue(delay);
        }

        return response;
    }
}
