namespace Xio.Parallax.Client;

/// <summary>
/// The look-up slot conversation on <see cref="ParallaxClient"/>: open (or resume), declare
/// hashes and upload only what is missing, and commit. A look-up commit is terminal and answers
/// the results directly, so this conversation never polls for them; it reads progress once, after
/// commit, purely to report it.
/// </summary>
public sealed partial class ParallaxClient
{
    private const string LookupSlotQueriesUrlTemplate = "{+baseurl}/lookup/slots/{lookupSlotId}/queries";

    /// <summary>
    /// Looks up a batch of images through one look-up slot: opens or resumes a slot, uploads only
    /// the images the slot is missing, and commits. The commit is terminal and answers the
    /// results directly, so this call does not poll; it reads <c>/progress</c> once, after commit,
    /// to report the final progress, and reads <c>/results</c> only if the commit response body
    /// came back empty. Two inputs with identical bytes declare and upload one hash once; the
    /// results, keyed by hash, carry that hash once. Running the same call again over the same
    /// images, naming the slot it opened via <see cref="LookupBatchOptions.ExistingLookupSlotId"/>,
    /// resumes after an interruption: only what the slot still lacks is uploaded.
    /// </summary>
    /// <param name="images">The images to look up.</param>
    /// <param name="options">Which look-up slot to resume.</param>
    /// <param name="progress">Reported once, with the progress read after commit.</param>
    /// <param name="cancellationToken">Cancels the whole conversation.</param>
    /// <returns>The look-up slot's id, its results, and its progress once committed.</returns>
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
            if (imagesByHash.TryAdd(hash, image))
            {
                orderedHashes.Add(hash);
            }
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

        var committed = await ExecuteNullableAsync(
            () => Api.Lookup.Slots[lookupSlotId].Commit.PostAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);

        var results = committed ?? await ExecuteAsync(
            () => Api.Lookup.Slots[lookupSlotId].Results.GetAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);

        var finalProgress = await ExecuteAsync(
            () => Api.Lookup.Slots[lookupSlotId].Progress.GetAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
        progress?.Report(finalProgress);

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
