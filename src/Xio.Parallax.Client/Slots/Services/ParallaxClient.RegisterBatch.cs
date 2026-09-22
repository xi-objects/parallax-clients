namespace Xio.Parallax.Client;

/// <summary>
/// The registration slot conversation on <see cref="ParallaxClient"/>: open (or resume), declare
/// hashes and upload only what is missing, commit, and poll to a terminal progress.
/// </summary>
public sealed partial class ParallaxClient
{
    private const string SlotUploadsUrlTemplate = "{+baseurl}/slots/{slotId}/uploads";

    /// <summary>
    /// Registers a batch of images through one slot: opens or resumes a slot, uploads only the
    /// images the slot is missing, commits, and polls until every entry has left the "retry"
    /// state. Running the same call again over the same items, naming the slot it opened via
    /// <see cref="RegisterBatchOptions.ExistingSlotId"/>, resumes after an interruption: only
    /// what the slot still lacks is uploaded. An image the account already registered is refused
    /// at upload and returned as-is, in the "errata" state; this call never throws for it.
    /// </summary>
    /// <param name="items">The images, and their manifests, to register.</param>
    /// <param name="options">How long to poll and for how long, and which slot to resume.</param>
    /// <param name="progress">Reported with every progress poll, including the final one.</param>
    /// <param name="cancellationToken">Cancels the whole conversation.</param>
    /// <returns>The slot's id, its commit, its final progress, and every upload outcome this run made.</returns>
    public async Task<RegisterBatchResult> RegisterBatchAsync(
        IReadOnlyList<RegistrationItem> items,
        RegisterBatchOptions options,
        IProgress<SlotProgressResponse>? progress,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(items);
        ArgumentNullException.ThrowIfNull(options);
        var batching = RequireBatching();

        var slotId = options.ExistingSlotId ?? await OpenSlotAsync(cancellationToken).ConfigureAwait(false);

        var itemsByHash = new Dictionary<string, RegistrationItem>(StringComparer.Ordinal);
        var orderedHashes = new List<string>(items.Count);
        foreach (var item in items)
        {
            var hash = Sha256Hex(item.Image.Bytes);
            orderedHashes.Add(hash);
            itemsByHash.TryAdd(hash, item);
        }

        var missingResponse = await ExecuteAsync(
            () => Api.Slots[slotId].Uploads.Missing.PostAsync(new ResumeRequestBody { Hashes = orderedHashes }, cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
        var missingHashes = missingResponse.Missing ?? new List<string>();
        var missingItems = missingHashes.Select(hash => itemsByHash[hash]).ToList();

        var uploadOutcomes = new List<SlotUploadOutcomeResponse>();
        foreach (var batch in ChunkByBatching(missingItems, batching, RegistrationItemSize))
        {
            var content = MultipartRequestContent.CreateForUpload(
                batch.Select(item => new ManifestedImage(item.Image, item.Manifests)).ToList());
            var pathParameters = new Dictionary<string, object>(StringComparer.Ordinal)
            {
                ["baseurl"] = _requestAdapter.BaseUrl!,
                ["slotId"] = slotId,
            };
            var uploadResponse = await ExecuteAsync(
                () => MultipartRequestSender.PostAsync(
                    _requestAdapter,
                    SlotUploadsUrlTemplate,
                    pathParameters,
                    content,
                    SlotUploadResponse.CreateFromDiscriminatorValue,
                    SlotUploadsErrorMapping,
                    cancellationToken),
                cancellationToken).ConfigureAwait(false);
            if (uploadResponse.Outcomes is not null)
            {
                uploadOutcomes.AddRange(uploadResponse.Outcomes);
            }
        }

        var commit = await ExecuteAsync(
            () => Api.Slots[slotId].Commit.PostAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);

        var finalProgress = await PollUntilNoRetryAsync(
            () => Api.Slots[slotId].Progress.GetAsync(cancellationToken: cancellationToken),
            slotId,
            options.PollInterval,
            options.PollTimeout,
            progress,
            cancellationToken).ConfigureAwait(false);

        return new RegisterBatchResult(slotId, commit, finalProgress, uploadOutcomes);
    }

    private async Task<string> OpenSlotAsync(CancellationToken cancellationToken)
    {
        var opened = await ExecuteAsync(
            () => Api.Slots.PostAsync(cancellationToken: cancellationToken),
            cancellationToken).ConfigureAwait(false);
        return opened.SlotId ?? throw new ParallaxClientException("The Parallax API opened a slot without naming its id.");
    }

    private static long RegistrationItemSize(RegistrationItem item)
        => item.Image.Bytes.Length + item.Manifests.Sum(manifest => (long)manifest.Bytes.Length);
}
