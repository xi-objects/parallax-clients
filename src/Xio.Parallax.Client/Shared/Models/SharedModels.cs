namespace Xio.Parallax.Client.Shared.Models;

/// <summary>
/// Configuration for a <see cref="ParallaxClient"/>: where the API lives, how the caller
/// authenticates, and the operator-configured batching caps.
/// </summary>
public sealed record ParallaxClientOptions
{
    /// <summary>
    /// The base address of the XI Parallax REST API. Defaults to the production endpoint.
    /// </summary>
    public Uri BaseAddress { get; init; } = new("https://api.parallax.xiobjects.com");

    /// <summary>The account bearer token, sent as the Authorization header when set.</summary>
    public string? AccountToken { get; init; }

    /// <summary>The admin key, sent as the X-Admin-Key header when set.</summary>
    public string? AdminKey { get; init; }

    /// <summary>
    /// The operator-configured upload batching caps. Left null, every batch call refuses rather
    /// than guessing at limits the OpenAPI document does not declare.
    /// </summary>
    public UploadBatching? Batching { get; init; }
}

/// <summary>
/// The operator-configured caps a batched slot upload must respect. Neither cap is declared by
/// the OpenAPI document, so the caller states them; there is no default.
/// </summary>
/// <param name="MaxRequestBytes">The maximum total byte size of one multipart upload request.</param>
/// <param name="MaxImagesPerRequest">The maximum number of images carried by one multipart upload request.</param>
public sealed record UploadBatching(long MaxRequestBytes,
                                     int MaxImagesPerRequest);
