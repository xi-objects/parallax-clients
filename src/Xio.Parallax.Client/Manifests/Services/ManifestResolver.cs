namespace Xio.Parallax.Client.Manifests.Services;

/// <summary>
/// Resolves manifest selections into manifest parts: JSON sidecars as given, JUMBF sidecars
/// classified c2pa or jumbf by the JUMBF walk, and, when the selection includes them, the embedded
/// JUMBF manifest stores merged in by Xio.Parallax.Manifests: every embedded store whose bytes are not
/// already in the list is added, C2PA or not. A malformed sidecar or embedding, more than one distinct
/// C2PA manifest, and two JSON manifests of one kind are refusals; over a collection every image is
/// evaluated first and any refusal refuses them all.
/// </summary>
public sealed class ManifestResolver : IManifestResolver
{
    private readonly IManifestMerger _merger;
    private readonly IJumbfStoreReader _jumbf;

    /// <summary>Creates the resolver over the manifest merge and JUMBF walk of Xio.Parallax.Manifests.</summary>
    public ManifestResolver()
        : this(C2paComposition.Merger, C2paComposition.JumbfReader)
    {
    }

    internal ManifestResolver(IManifestMerger merger,
                              IJumbfStoreReader jumbf)
    {
        _merger = merger;
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

            if (!parts.Any(part => part.Form != ManifestForm.Json && part.Bytes.Span.SequenceEqual(sidecar.Bytes.Span)))
            {
                parts.Add(new ManifestPart(kind, C2paAttachment.FormOf(kind), sidecar.Bytes));
            }
        }

        if (selection.IncludeEmbedded)
        {
            var merged = _merger.Merge(image.Bytes, [.. parts.Select(ToEntry)]);
            switch (merged.Outcome)
            {
                case ManifestMergeOutcome.Merged:
                    parts = [.. merged.Manifests.Select(ToPart)];
                    break;
                case ManifestMergeOutcome.Conflict:
                    return Resolution.Refused($"Its manifests conflict: {merged.Detail}");
                case ManifestMergeOutcome.Malformed:
                    return Resolution.Refused($"Its embedded JUMBF manifest store is malformed: {merged.Detail}");
                default:
                    throw new ArgumentOutOfRangeException(nameof(image), merged.Outcome, "Unknown merge outcome; there is no default.");
            }
        }

        return Repeated(parts) is { } refusal ? Resolution.Refused(refusal) : new Resolution(parts, null);
    }

    private static string? Repeated(IReadOnlyList<ManifestPart> parts)
    {
        var c2pa = parts.Count(part => part.Kind == JumbfKinds.C2pa);
        if (c2pa > 1)
        {
            return $"{c2pa} distinct C2PA manifests across its sidecars and embedded stores; an image carries at most one.";
        }

        var repeated = parts.Where(part => part.Form == ManifestForm.Json)
            .GroupBy(part => part.Kind)
            .FirstOrDefault(group => group.Count() > 1);
        return repeated is null
            ? null
            : $"{repeated.Count()} JSON manifests of kind '{repeated.Key}'; one JSON kind carries one manifest.";
    }

    private string? ClassifySidecar(ReadOnlyMemory<byte> bytes, out string? failure)
    {
        try
        {
            _jumbf.Summarise(bytes.Span);
            failure = null;
            return _jumbf.Classify(bytes.Span);
        }
        catch (JumbfFormatException exception)
        {
            failure = exception.Message;
            return null;
        }
    }

    private static ImageManifestEntry ToEntry(ManifestPart part)
    {
        var form = part.Form switch
        {
            ManifestForm.Json => ManifestPayloadForm.Json,
            ManifestForm.Jumbf or ManifestForm.C2pa => ManifestPayloadForm.Jumbf,
            _ => throw new ArgumentOutOfRangeException(nameof(part), part.Form, "Unknown manifest form; there is no default."),
        };
        return new ImageManifestEntry(part.Kind, form, part.Bytes);
    }

    private static ManifestPart ToPart(ImageManifestEntry entry)
    {
        var form = entry.Form switch
        {
            ManifestPayloadForm.Json => ManifestForm.Json,
            ManifestPayloadForm.Jumbf => C2paAttachment.FormOf(entry.Kind),
            _ => throw new ArgumentOutOfRangeException(nameof(entry), entry.Form, "Unknown manifest payload form; there is no default."),
        };
        return new ManifestPart(entry.Kind, form, entry.Payload);
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
