namespace Xio.Parallax.Client;

/// <summary>
/// A client for the XI Parallax REST API: wires the generated <see cref="ParallaxApiClient"/>
/// with authentication, wraps every refusal as a <see cref="ParallaxProblemException"/>, and adds
/// the multipart uploads and slot conversations the generator cannot produce.
/// </summary>
public sealed partial class ParallaxClient : IDisposable
{
    private static readonly Dictionary<string, ParsableFactory<IParsable>> RegistrationsErrorMapping =
        BuildErrorMapping(400, 401, 409, 413, 415, 422, 429, 503);

    private static readonly Dictionary<string, ParsableFactory<IParsable>> SlotUploadsErrorMapping =
        BuildErrorMapping(400, 401, 404, 409, 413, 429, 503);

    private static readonly Dictionary<string, ParsableFactory<IParsable>> LookupErrorMapping =
        BuildErrorMapping(400, 401, 413, 422, 429, 503);

    private static readonly Dictionary<string, ParsableFactory<IParsable>> LookupQueriesErrorMapping =
        BuildErrorMapping(400, 401, 404, 409, 413, 429, 503);

    private readonly HttpClient _httpClient;
    private readonly bool _ownsHttpClient;
    private readonly HttpClientRequestAdapter _requestAdapter;
    private readonly ParallaxClientOptions _options;

    /// <summary>
    /// Creates a client from the given options, using the given <see cref="HttpClient"/> when
    /// supplied, or a new one owned by this client otherwise.
    /// </summary>
    /// <param name="options">Where the API lives, how the caller authenticates, and the batching caps.</param>
    /// <param name="httpClient">
    /// An existing <see cref="HttpClient"/> to send requests through; when omitted, this client
    /// creates and owns one.
    /// </param>
    public ParallaxClient(ParallaxClientOptions options, HttpClient? httpClient = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        _options = options;
        _ownsHttpClient = httpClient is null;
        _httpClient = httpClient ?? new HttpClient();
        var authenticationProvider = new ParallaxAuthenticationProvider(options.AccountToken, options.AdminKey);
        _requestAdapter = new HttpClientRequestAdapter(authenticationProvider, httpClient: _httpClient)
        {
            BaseUrl = options.BaseAddress.ToString().TrimEnd('/'),
        };
        Api = new ParallaxApiClient(_requestAdapter);
    }

    /// <summary>The generated API client, wired with this client's base address and authentication.</summary>
    public ParallaxApiClient Api { get; }

    /// <summary>
    /// Disposes the request adapter, and the <see cref="HttpClient"/> this client created; does
    /// nothing to an <see cref="HttpClient"/> the caller supplied.
    /// </summary>
    public void Dispose()
    {
        _requestAdapter.Dispose();
        if (_ownsHttpClient)
        {
            _httpClient.Dispose();
        }
    }

    private static Dictionary<string, ParsableFactory<IParsable>> BuildErrorMapping(params int[] statusCodes)
    {
        var mapping = new Dictionary<string, ParsableFactory<IParsable>>();
        foreach (var statusCode in statusCodes)
        {
            mapping[statusCode.ToString(CultureInfo.InvariantCulture)] = ProblemDetails.CreateFromDiscriminatorValue;
        }

        return mapping;
    }

    private Dictionary<string, object> RootPathParameters()
        => new(StringComparer.Ordinal) { ["baseurl"] = _requestAdapter.BaseUrl! };

    private async Task<T> ExecuteAsync<T>(Func<Task<T?>> call, CancellationToken cancellationToken)
        where T : class
    {
        var result = await ExecuteNullableAsync(call, cancellationToken).ConfigureAwait(false);
        if (result is null)
        {
            throw new ParallaxClientException("The Parallax API returned an empty response body where a value was expected.");
        }

        return result;
    }

    /// <summary>
    /// Runs <paramref name="call"/> the same way <see cref="ExecuteAsync{T}"/> does, but returns
    /// an empty body as <see langword="null"/> instead of throwing: for the few calls, such as a
    /// look-up commit, where an empty body is a meaningful outcome the caller falls back from.
    /// </summary>
    private async Task<T?> ExecuteNullableAsync<T>(Func<Task<T?>> call, CancellationToken cancellationToken)
        where T : class
    {
        T? result = null;
        await ExecuteCoreAsync(
            async () => { result = await call().ConfigureAwait(false); },
            cancellationToken).ConfigureAwait(false);
        return result;
    }

    private async Task ExecuteAsync(Func<Task> call, CancellationToken cancellationToken)
        => await ExecuteCoreAsync(call, cancellationToken).ConfigureAwait(false);

    /// <summary>
    /// The one helper every hand-written call goes through: runs the call, and on an API refusal
    /// wraps it as a <see cref="ParallaxProblemException"/>. A 503 whose Retry-After header is
    /// present (the "image could not be checked yet" refusal, the only 503 that carries one) is
    /// retried exactly once after waiting that long; nothing else is retried silently.
    /// </summary>
    private static async Task ExecuteCoreAsync(Func<Task> call, CancellationToken cancellationToken)
    {
        try
        {
            await call().ConfigureAwait(false);
        }
        catch (ApiException ex)
        {
            var retryAfter = ParallaxProblemException.TryReadRetryAfter(ex);
            if (ex.ResponseStatusCode == 503 && retryAfter is { } delay)
            {
                await Task.Delay(delay, cancellationToken).ConfigureAwait(false);
                try
                {
                    await call().ConfigureAwait(false);
                    return;
                }
                catch (ApiException retryEx)
                {
                    throw ParallaxProblemException.FromApiException(retryEx);
                }
            }

            throw ParallaxProblemException.FromApiException(ex);
        }
    }
}
