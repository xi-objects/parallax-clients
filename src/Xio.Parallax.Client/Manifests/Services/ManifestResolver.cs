namespace Xio.Parallax.Client.Manifests.Services;

/// <summary>
/// Resolves manifest selections into manifest parts: JSON sidecars as given, JUMBF sidecars and
/// embedded JUMBF manifest stores classified c2pa or jumbf by the JUMBF walk. A JUMBF sidecar that
/// differs from an embedded store, a malformed store or sidecar, an unrecognised carrier whenever
/// the embedded store matters, and two manifests of one kind are refusals; over a collection every
/// image is evaluated first and any refusal refuses them all.
/// </summary>
public sealed class ManifestResolver : IManifestResolver
{
    private readonly IEmbeddedC2paDetector _detector;
    private readonly IJumbfStoreReader _jumbf;

    /// <summary>Creates the resolver over the built-in detector and JUMBF reader.</summary>
    public ManifestResolver()
        : this(new EmbeddedC2paDetector(), C2paComposition.JumbfReader)
    {
    }

    internal ManifestResolver(IEmbeddedC2paDetector detector,
                              IJumbfStoreReader jumbf)
    {
        _detector = detector;
        _jumbf = jumbf;
    }

    /// <inheritdoc/>
    public IReadOnlyList<RegistrationItem> Resolve(IReadOnlyList<ManifestRequest> requests)
    {
        ArgumentNullException.ThrowIfNull(requests);
        var items = new List<RegistrationItem>();
        var refusals = new List<ManifestRefusal>();
        foreach (var request in requests)
        {
            ArgumentNullException.ThrowIfNull(request);
            var resolution = Evaluate(request.Image, request.Selection);
            if (resolution.Reason is not null)
            {
                refusals.Add(new ManifestRefusal(request.Image.FileName, resolution.Reason));
                continue;
            }

            items.Add(new RegistrationItem(request.Image, resolution.Parts));
        }

        return refusals.Count == 0 ? items : throw new ManifestRefusalException(refusals);
    }

    /// <inheritdoc/>
    public IReadOnlyList<ManifestPart> Resolve(ImageUpload image, ManifestSelection selection)
    {
        var resolution = Evaluate(image, selection);
        return resolution.Reason is null
            ? resolution.Parts
            : throw new ManifestRefusalException([new ManifestRefusal(image.FileName, resolution.Reason)]);
    }

    private Resolution Evaluate(ImageUpload image, ManifestSelection selection)
    {
        ArgumentNullException.ThrowIfNull(image);
        ArgumentNullException.ThrowIfNull(selection);
        var parts = new List<ManifestPart>();
        var jumbfSidecars = new List<ReadOnlyMemory<byte>>();
        foreach (var sidecar in selection.Sidecars)
        {
            if (sidecar.Form == ManifestForm.Json)
            {
                parts.Add(new ManifestPart(sidecar.Kind!, ManifestForm.Json, sidecar.Bytes));
                continue;
            }

            var kind = ClassifySidecar(sidecar.Bytes, out var failure);
            if (kind is null)
            {
                return Resolution.Refused($"JUMBF sidecar '{sidecar.Name}' is malformed: {failure}");
            }

            if (jumbfSidecars.Any(included => included.Span.SequenceEqual(sidecar.Bytes.Span)))
            {
                continue;
            }

            parts.Add(new ManifestPart(kind, C2paAttachment.FormOf(kind), sidecar.Bytes));
            jumbfSidecars.Add(sidecar.Bytes);
        }

        if (selection.IncludeEmbedded || jumbfSidecars.Count > 0)
        {
            var embedded = _detector.Detect(image.Bytes);
            var refusal = EmbeddedRefusal(embedded, selection.Sidecars, jumbfSidecars);
            if (refusal is not null)
            {
                return Resolution.Refused(refusal);
            }

            if (selection.IncludeEmbedded)
            {
                parts.AddRange(embedded.Stores
                    .Where(store => !jumbfSidecars.Any(sidecar => sidecar.Span.SequenceEqual(store.Bytes.Span)))
                    .Select(C2paAttachment.AsManifestPart));
            }
        }

        var repeated = parts.GroupBy(part => part.Kind).FirstOrDefault(group => group.Count() > 1);
        return repeated is null
            ? new Resolution(parts, null)
            : Resolution.Refused($"{repeated.Count()} manifests of kind '{repeated.Key}' across its sidecars and embedded stores; one kind carries one manifest.");
    }

    private string? ClassifySidecar(ReadOnlyMemory<byte> bytes, out string? failure)
    {
        try
        {
            _jumbf.Summarise(bytes.Span);
            failure = null;
            return _jumbf.Classify(bytes.Span);
        }
        catch (C2paFormatException exception)
        {
            failure = exception.Message;
            return null;
        }
    }

    private static string? EmbeddedRefusal(EmbeddedC2paResult embedded, IReadOnlyList<SidecarManifest> sidecars, List<ReadOnlyMemory<byte>> jumbfSidecars)
    {
        switch (embedded.Outcome)
        {
            case EmbeddedC2paOutcome.Unsupported:
                return $"Its carrier is not recognised, so whether it embeds a JUMBF manifest store cannot be said: {embedded.Detail}";
            case EmbeddedC2paOutcome.Malformed:
                return $"Its embedded JUMBF manifest store is malformed: {embedded.Detail}";
            case EmbeddedC2paOutcome.Absent:
                return null;
            case EmbeddedC2paOutcome.Found:
                if (jumbfSidecars.Count == 0)
                {
                    return null;
                }

                var unmatchedStore = embedded.Stores.FirstOrDefault(store => !jumbfSidecars.Any(sidecar => sidecar.Span.SequenceEqual(store.Bytes.Span)));
                if (unmatchedStore is not null)
                {
                    return $"Its embedded {unmatchedStore.Kind} manifest store differs from its JUMBF sidecar(s); embedded stores and JUMBF sidecars must be the same bytes.";
                }

                var unmatchedSidecar = sidecars.FirstOrDefault(sidecar => sidecar.Form == ManifestForm.Jumbf
                    && !embedded.Stores.Any(store => store.Bytes.Span.SequenceEqual(sidecar.Bytes.Span)));
                return unmatchedSidecar is null
                    ? null
                    : $"Its JUMBF sidecar '{unmatchedSidecar.Name}' matches no embedded manifest store; embedded stores and JUMBF sidecars must be the same bytes.";
            default:
                throw new ArgumentOutOfRangeException(nameof(embedded), embedded.Outcome, "Unknown embedded outcome; there is no default.");
        }
    }

    /// <summary>One image's resolution: its parts in wire order, or the one reason it was refused.</summary>
    private sealed record Resolution(IReadOnlyList<ManifestPart> Parts,
                                     string? Reason)
    {
        public static Resolution Refused(string reason)
        {
            return new Resolution([], reason);
        }
    }
}
