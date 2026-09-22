namespace Xio.Parallax.Client.Problems;

/// <summary>
/// A typed refusal from the XI Parallax REST API: the problem+json fields the server sent,
/// wrapped so a caller never has to inspect the generated exception directly.
/// </summary>
public sealed class ParallaxProblemException : Exception
{
    private const string ProblemTypePrefix = "urn:xio:parallax:problem:";

    private ParallaxProblemException(
        string message,
        int? status,
        string? type,
        string? title,
        string? detail,
        string? traceId,
        string? cap,
        Guid? registrationId,
        int? registrationRemaining,
        int? lookupRemaining,
        TimeSpan? retryAfter)
        : base(message)
    {
        Status = status;
        Type = type;
        Slug = ExtractSlug(type);
        Title = title;
        Detail = detail;
        TraceId = traceId;
        Cap = cap;
        RegistrationId = registrationId;
        RegistrationRemaining = registrationRemaining;
        LookupRemaining = lookupRemaining;
        RetryAfter = retryAfter;
    }

    /// <summary>The HTTP status code the server refused with.</summary>
    public int? Status { get; }

    /// <summary>The problem's URN type, in the form urn:xio:parallax:problem:&lt;slug&gt;.</summary>
    public string? Type { get; }

    /// <summary>The slug segment of <see cref="Type"/>: the part after the URN prefix.</summary>
    public string? Slug { get; }

    /// <summary>The problem's short, human-readable title.</summary>
    public string? Title { get; }

    /// <summary>The problem's longer, human-readable detail.</summary>
    public string? Detail { get; }

    /// <summary>The server's trace identifier for the refused request, when it sent one.</summary>
    public string? TraceId { get; }

    /// <summary>The operator-configured cap the request exceeded, when the problem names one.</summary>
    public string? Cap { get; }

    /// <summary>The caller's own already-registered registration, when the problem names one.</summary>
    public Guid? RegistrationId { get; }

    /// <summary>How many registrations the account has left, when the problem reports it.</summary>
    public int? RegistrationRemaining { get; }

    /// <summary>How many look-ups the account has left, when the problem reports it.</summary>
    public int? LookupRemaining { get; }

    /// <summary>
    /// How long to wait before retrying, present only on the 503 that means the image could not
    /// be checked yet.
    /// </summary>
    public TimeSpan? RetryAfter { get; }

    /// <summary>
    /// Builds a <see cref="ParallaxProblemException"/> from whatever the generated client threw:
    /// the full problem+json fields when the failure carried one, or just the response status
    /// otherwise.
    /// </summary>
    /// <param name="exception">The failure the generated client's request adapter threw.</param>
    /// <returns>A typed wrapper carrying every field this library surfaces.</returns>
    internal static ParallaxProblemException FromApiException(ApiException exception)
    {
        ArgumentNullException.ThrowIfNull(exception);
        if (exception is ProblemDetails problem)
        {
            var status = problem.Status ?? problem.ResponseStatusCode;
            return new ParallaxProblemException(
                BuildMessage(status, problem.Title, problem.Detail),
                status,
                problem.Type,
                problem.Title,
                problem.Detail,
                ReadString(problem.AdditionalData, "traceId"),
                ReadString(problem.AdditionalData, "cap"),
                ReadGuid(problem.AdditionalData, "registrationId"),
                ReadInt(problem.AdditionalData, "registrationRemaining"),
                ReadInt(problem.AdditionalData, "lookupRemaining"),
                TryReadRetryAfter(problem));
        }

        return new ParallaxProblemException(
            BuildMessage(exception.ResponseStatusCode, null, exception.Message),
            exception.ResponseStatusCode,
            type: null,
            title: null,
            detail: exception.Message,
            traceId: null,
            cap: null,
            registrationId: null,
            registrationRemaining: null,
            lookupRemaining: null,
            TryReadRetryAfter(exception));
    }

    /// <summary>
    /// Reads the Retry-After header, in whole seconds, from a generated-client failure. Present
    /// only on the 503 that means the image could not be checked yet.
    /// </summary>
    /// <param name="exception">The failure to read response headers from.</param>
    /// <returns>The wait duration, or null when no valid Retry-After header was sent.</returns>
    internal static TimeSpan? TryReadRetryAfter(ApiException exception)
    {
        var headers = exception.ResponseHeaders;
        if (headers is null)
        {
            return null;
        }

        foreach (var pair in headers)
        {
            if (!string.Equals(pair.Key, "Retry-After", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var raw = pair.Value?.FirstOrDefault();
            if (raw is not null
                && int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var seconds)
                && seconds >= 0)
            {
                return TimeSpan.FromSeconds(seconds);
            }
        }

        return null;
    }

    private static string BuildMessage(int? status, string? title, string? detail)
    {
        var reason = title ?? detail ?? "no detail given";
        return status is { } code
            ? $"The Parallax API refused ({code}): {reason}"
            : $"The Parallax API refused: {reason}";
    }

    private static string? ExtractSlug(string? type)
    {
        return type is not null && type.StartsWith(ProblemTypePrefix, StringComparison.Ordinal)
            ? type[ProblemTypePrefix.Length..]
            : null;
    }

    private static string? ReadString(IDictionary<string, object> additionalData, string key)
    {
        return additionalData.TryGetValue(key, out var value) && value is string text ? text : null;
    }

    private static Guid? ReadGuid(IDictionary<string, object> additionalData, string key)
    {
        if (!additionalData.TryGetValue(key, out var value))
        {
            return null;
        }

        return value switch
        {
            Guid guid => guid,
            string text when Guid.TryParse(text, out var parsed) => parsed,
            _ => null,
        };
    }

    private static int? ReadInt(IDictionary<string, object> additionalData, string key)
    {
        if (!additionalData.TryGetValue(key, out var value))
        {
            return null;
        }

        return value switch
        {
            int i => i,
            long l => (int)l,
            decimal d => (int)d,
            double d => (int)d,
            string text when int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed) => parsed,
            _ => null,
        };
    }
}
