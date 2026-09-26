namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Compares an embedded JUMBF manifest store with a recovered record: BLAKE3-256 of the store bytes against the declared hash of each jumbf-form manifest, never a json-form one.</summary>
public sealed class C2paRecordComparer : IC2paRecordComparer
{
    /// <inheritdoc/>
    public C2paComparison Compare(EmbeddedC2paStore store, PublishedRecordResponse record)
    {
        ArgumentNullException.ThrowIfNull(store);
        ArgumentNullException.ThrowIfNull(record);
        if (record.Outcome != PublishedRecordOutcome.Published)
        {
            return new C2paComparison(C2paComparisonOutcome.NotPublished, null, $"The record's outcome is '{record.Outcome?.ToString() ?? "absent"}', not published.");
        }

        var candidates = (record.Manifests ?? [])
            .Where(manifest => manifest.Form == PublishedRecordResponse_manifests_form.Jumbf)
            .ToList();
        if (candidates.Count == 0)
        {
            return new C2paComparison(C2paComparisonOutcome.AbsentFromRecord, null, "The record carries no jumbf-form manifest.");
        }

        var storeHash = Blake3Hasher.Hash(store.Bytes.Span);
        var matched = candidates.FirstOrDefault(manifest => DeclaresHash(manifest.Hash, storeHash.AsSpan()));
        return matched is null
            ? new C2paComparison(C2paComparisonOutcome.Mismatch, null, $"None of the record's {candidates.Count} jumbf-form manifest(s) declares the store's BLAKE3-256 hash.")
            : new C2paComparison(C2paComparisonOutcome.Match, matched.Type, $"BLAKE3-256 of the store bytes equals the declared hash of the record's '{matched.Type}' manifest.");
    }

    private static bool DeclaresHash(string? declared, ReadOnlySpan<byte> storeHash)
    {
        if (declared is null || declared.Length != storeHash.Length * 2)
        {
            return false;
        }

        try
        {
            return Convert.FromHexString(declared).AsSpan().SequenceEqual(storeHash);
        }
        catch (FormatException)
        {
            return false;
        }
    }
}
