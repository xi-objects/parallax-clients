namespace Xio.Parallax.Client.C2pa.Interfaces;

/// <summary>Compares an embedded C2PA store with a recovered record's jumbf-form manifests, by bytes.</summary>
public interface IC2paRecordComparer
{
    /// <summary>Compares the BLAKE3-256 of the store bytes with the declared hash of each jumbf-form manifest of the record.</summary>
    /// <param name="store">The store extracted from the file.</param>
    /// <param name="record">The record recovered for the file.</param>
    /// <returns>The outcome, the matched manifest's kind on a match, and a description.</returns>
    C2paComparison Compare(EmbeddedC2paStore store, PublishedRecordResponse record);
}
