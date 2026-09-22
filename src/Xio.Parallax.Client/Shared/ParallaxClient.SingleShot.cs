namespace Xio.Parallax.Client;

/// <summary>
/// The single-shot calls on <see cref="ParallaxClient"/>: register, look up, recover and take
/// down one image at a time, plus account and health status.
/// </summary>
public sealed partial class ParallaxClient
{
    private const string RegistrationsUrlTemplate = "{+baseurl}/registrations";
    private const string LookupUrlTemplate = "{+baseurl}/lookup";

    /// <summary>Registers one image, and the manifests it carries, in a single request.</summary>
    /// <param name="image">The image to register.</param>
    /// <param name="manifests">The manifests the image carries, in the order they precede it on the wire.</param>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>The registration this image received.</returns>
    public async Task<RegisterSingleResponse> RegisterAsync(
        ImageUpload image,
        IReadOnlyList<ManifestPart> manifests,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(image);
        ArgumentNullException.ThrowIfNull(manifests);
        var content = MultipartRequestContent.CreateForUpload(new[] { new ManifestedImage(image, manifests) });
        return await ExecuteAsync(
            () => MultipartRequestSender.PostAsync(
                _requestAdapter,
                RegistrationsUrlTemplate,
                RootPathParameters(),
                content,
                RegisterSingleResponse.CreateFromDiscriminatorValue,
                RegistrationsErrorMapping,
                cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Looks one image up: is it registered, and is the match the caller's own?</summary>
    /// <param name="image">The image to look up.</param>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>Whether the image matched, and the candidates found.</returns>
    public async Task<LookupResponse> LookupAsync(ImageUpload image, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(image);
        var content = MultipartRequestContent.CreateForLookup(new[] { image });
        return await ExecuteAsync(
            () => MultipartRequestSender.PostAsync(
                _requestAdapter,
                LookupUrlTemplate,
                RootPathParameters(),
                content,
                LookupResponse.CreateFromDiscriminatorValue,
                LookupErrorMapping,
                cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Recovers the published record for one original image hash.</summary>
    /// <param name="originalImageHash">The SHA-256 hash, lowercase hex, that keys the record.</param>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>The published record, its manifests and its verification block.</returns>
    public async Task<PublishedRecordResponse> GetRecordAsync(string originalImageHash, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrEmpty(originalImageHash);
        return await ExecuteAsync(
            () => Api.Records[originalImageHash].GetAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Recovers the published records for a batch of original image hashes.</summary>
    /// <param name="hashes">The SHA-256 hashes, lowercase hex, that key the records.</param>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>The published records found for the given hashes.</returns>
    public async Task<PublishedRecordsResponse> GetRecordsAsync(IReadOnlyList<string> hashes, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(hashes);
        var body = new PublishedRecordsRequestBody { OriginalImageHashes = hashes.ToList() };
        return await ExecuteAsync(
            () => Api.Records.PostAsync(body, cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Takes a registration down.</summary>
    /// <param name="registrationId">The registration to take down.</param>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>A task that completes once the registration is taken down.</returns>
    public async Task UnregisterAsync(Guid registrationId, CancellationToken cancellationToken = default)
    {
        await ExecuteAsync(
            () => Api.Registrations[registrationId].DeleteAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Reports the calling account's registration and look-up grants.</summary>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>The account's call count and its registration and look-up grants.</returns>
    public async Task<AccountStatsResponse> GetAccountStatsAsync(CancellationToken cancellationToken = default)
    {
        return await ExecuteAsync(
            () => Api.Account.Stats.GetAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Reports the service's health, anonymously.</summary>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>The service's name and version.</returns>
    public async Task<HealthResponse> GetHealthAsync(CancellationToken cancellationToken = default)
    {
        return await ExecuteAsync(
            () => Api.Health.GetAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
    }
}
