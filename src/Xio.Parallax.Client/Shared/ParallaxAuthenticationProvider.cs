namespace Xio.Parallax.Client.Shared;

/// <summary>
/// Adds the account bearer token and the admin key to every outgoing request, whichever the
/// caller supplied. Never logs or otherwise surfaces either value.
/// </summary>
internal sealed class ParallaxAuthenticationProvider : IAuthenticationProvider
{
    private readonly string? _accountToken;
    private readonly string? _adminKey;

    /// <summary>
    /// Creates a provider that sends the given bearer token and admin key, whichever are set.
    /// </summary>
    /// <param name="accountToken">The account bearer token, or null to send none.</param>
    /// <param name="adminKey">The admin key, or null to send none.</param>
    internal ParallaxAuthenticationProvider(string? accountToken, string? adminKey)
    {
        _accountToken = accountToken;
        _adminKey = adminKey;
    }

    /// <summary>
    /// Adds the Authorization and X-Admin-Key headers to the given request, whichever apply.
    /// </summary>
    /// <param name="request">The request to authenticate.</param>
    /// <param name="additionalAuthenticationContext">Unused; this provider needs no extra context.</param>
    /// <param name="cancellationToken">Unused; adding headers never awaits anything.</param>
    /// <returns>A completed task; this provider never has to wait.</returns>
    public Task AuthenticateRequestAsync(
        RequestInformation request,
        Dictionary<string, object>? additionalAuthenticationContext = null,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (!string.IsNullOrEmpty(_accountToken))
        {
            request.Headers.TryAdd("Authorization", $"Bearer {_accountToken}");
        }

        if (!string.IsNullOrEmpty(_adminKey))
        {
            request.Headers.TryAdd("X-Admin-Key", _adminKey);
        }

        return Task.CompletedTask;
    }
}
