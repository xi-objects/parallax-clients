namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Pins the roots Orbital distributes from its anonymous discovery route.</summary>
public interface IOrbitalTrustRootSource
{
    /// <summary>GETs <c>{orbitalBaseUrl}/info</c> anonymously and pins its <c>pinnedRoots</c> PEM array. The URL should be https; the scheme it names is the scheme used.</summary>
    /// <exception cref="VerificationRefusedException">Orbital did not answer with success, answered without <c>pinnedRoots</c>, or with an empty list (Control not activated).</exception>
    Task<TrustRoots> FetchAsync(Uri orbitalBaseUrl, CancellationToken cancellationToken);
}

/// <summary>Pins the roots Orbital distributes, over the given HTTP client.</summary>
public sealed class OrbitalTrustRootSource : IOrbitalTrustRootSource
{
    private readonly HttpClient _http;
    private readonly ITrustRootReader _reader;

    /// <summary>Creates the source over the HTTP client that makes the request.</summary>
    public OrbitalTrustRootSource(HttpClient http)
        : this(http, new TrustRootReader())
    {
    }

    internal OrbitalTrustRootSource(HttpClient http,
                                    ITrustRootReader reader)
    {
        ArgumentNullException.ThrowIfNull(http);
        _http = http;
        _reader = reader;
    }

    /// <inheritdoc/>
    public async Task<TrustRoots> FetchAsync(Uri orbitalBaseUrl, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(orbitalBaseUrl);
        try
        {
            var infoUrl = new Uri(orbitalBaseUrl.AbsoluteUri.TrimEnd('/') + VerificationConstants.OrbitalInfoPath);
            using var response = await _http
                .GetAsync(infoUrl, cancellationToken)
                .ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
            {
                throw new VerificationRefusedException($"Orbital {infoUrl} answered {(int)response.StatusCode}; no roots pinned.");
            }

            var body = await response.Content
                .ReadAsStreamAsync(cancellationToken)
                .ConfigureAwait(false);
            await using (body.ConfigureAwait(false))
            {
                using var document = await JsonDocument
                    .ParseAsync(body, cancellationToken: cancellationToken)
                    .ConfigureAwait(false);
                return _reader.FromPem(ReadPinnedRoots(document.RootElement, infoUrl));
            }
        }
        catch (OperationCanceledException)
        {
            throw;
        }
    }

    private static List<string> ReadPinnedRoots(JsonElement root, Uri infoUrl)
    {
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new VerificationRefusedException($"Orbital {infoUrl} did not answer with a JSON object.");
        }

        foreach (var property in root.EnumerateObject())
        {
            if (!string.Equals(property.Name, VerificationConstants.OrbitalPinnedRootsProperty, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (property.Value.ValueKind != JsonValueKind.Array)
            {
                throw new VerificationRefusedException($"Orbital {infoUrl} answered pinnedRoots that is not an array.");
            }

            var pems = new List<string>();
            foreach (var item in property.Value.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.String)
                {
                    throw new VerificationRefusedException($"Orbital {infoUrl} answered a pinnedRoots entry that is not a string.");
                }

                pems.Add(item.GetString()!);
            }

            if (pems.Count == 0)
            {
                throw new VerificationRefusedException("Control not activated: no roots.");
            }

            return pems;
        }

        throw new VerificationRefusedException($"Orbital {infoUrl} answered without pinnedRoots.");
    }
}
