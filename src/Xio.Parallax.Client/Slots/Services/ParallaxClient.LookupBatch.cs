namespace Xio.Parallax.Client;

/// <summary>
/// The look-up slot conversation on <see cref="ParallaxClient"/>: open (or resume), declare
/// hashes and upload only what is missing, commit, poll to a terminal progress, and recover the
/// results.
/// </summary>
public sealed partial class ParallaxClient
{
    private const string LookupSlotQueriesUrlTemplate = "{+baseurl}/lookup/slots/{lookupSlotId}/queries";

    /// <summary>
    /// Looks up a batch of images through one look-up slot: opens or resumes a slot, uploads only
    /// the images the slot is missing, commits, polls until every entry has left the "retry"
    /// state, and recovers the final results. Running the same call again over the same images,
    /// naming the slot it opened via <see cref="LookupBatchOptions.ExistingLookupSlotId"/>,
    /// resumes after an interruption: only what the slot still lacks is uploaded.
    /// </summary>
    /// <param name="images">The images to look up.</param>
    /// <param name="options">How long to poll and for how long, and which look-up slot to resume.</param>
    /// <param name="progress">Reported with every progress poll, including the final one.</param>
    /// <param name="cancellationToken">Cancels the whole conversation.</param>
    /// <returns>The look-up slot's id, its final results, and its final progress.</returns>
    public async Task<LookupBatchResult> LookupBatchAsync(
        IReadOnlyList<ImageUpload> images,
        LookupBatchOptions options,
        IProgress<SlotProgressResponse>? progress,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(images);
        ArgumentNullException.ThrowIfNull(options);
        var batching = RequireBatching();

        var lookupSlotId = options.ExistingLookupSlotId ?? await OpenLookupSlotAsync(cancellationToken).ConfigureAwait(false);

        var imagesByHash = new Dictionary<string, ImageUpload>(StringComparer.Ordinal);
        var orderedHashes = new List<string>(images.Count);
        foreach (var image in images)
        {
            var hash = Sha256Hex(image.Bytes);
            orderedHashes.Add(hash);
            imagesByHash.TryAdd(hash, image);
        }

        var missingResponse = await ExecuteAsync(
            () => Api.Lookup.Slots[lookupSlotId].Queries.Missing.PostAsync(new ResumeRequestBody { Hashes = orderedHashes }, cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
        var missingHashes = missingResponse.Missing ?? new List<string>();
        var missingImages = missingHashes.Select(hash => imagesByHash[hash]).ToList();

        var pathParameters = new Dictionary<string, object>(StringComparer.Ordinal)
        {
            ["baseurl"] = _requestAdapter.BaseUrl!,
            ["lookupSlotId"] = lookupSlotId,
        };
        foreach (var batch in ChunkByBatching(missingImages, batching, ImageUploadSize))
        {
            var content = MultipartRequestContent.CreateForLookup(batch);
            await ExecuteAsync(
                () => MultipartRequestSender.PostAsync(
                    _requestAdapter,
                    LookupSlotQueriesUrlTemplate,
                    pathParameters,
                    content,
                    SlotUploadResponse.CreateFromDiscriminatorValue,
                    LookupQueriesErrorMapping,
                    cancellationToken),
                cancellationToken).ConfigureAwait(false);
        }

        await ExecuteAsync(
            () => Api.Lookup.Slots[lookupSlotId].Commit.PostAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);

        var finalProgress = await PollUntilNoRetryAsync(
            () => Api.Lookup.Slots[lookupSlotId].Progress.GetAsync(cancellationToken: cancellationToken),
            lookupSlotId,
            options.PollInterval,
            options.PollTimeout,
            progress,
            cancellationToken).ConfigureAwait(false);

        var results = await ExecuteAsync(
            () => Api.Lookup.Slots[lookupSlotId].Results.GetAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);

        return new LookupBatchResult(lookupSlotId, results, finalProgress);
    }

    private async Task<string> OpenLookupSlotAsync(CancellationToken cancellationToken)
    {
        var opened = await ExecuteAsync(
            () => Api.Lookup.Slots.PostAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
        return opened.LookupSlotId ?? throw new ParallaxClientException("The Parallax API opened a look-up slot without naming its id.");
    }

    private static long ImageUploadSize(ImageUpload image)
        => image.Bytes.Length;
}
