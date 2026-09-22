namespace Xio.Parallax.Client.Verification.Models;

/// <summary>Asks for the per-manifest preimage.</summary>
/// <param name="ContentHash">The record's content hash bytes.</param>
/// <param name="Kind">The manifest kind (its type).</param>
/// <param name="ManifestHash">The manifest's hash bytes.</param>
public sealed record XioManifestPreimageRequest(ReadOnlyMemory<byte> ContentHash,
                                                string Kind,
                                                ReadOnlyMemory<byte> ManifestHash);

/// <summary>Asks for the collection preimage.</summary>
/// <param name="ContentHash">The record's content hash bytes.</param>
/// <param name="Manifests">Each manifest's kind and hash bytes, in record order.</param>
public sealed record XioCollectionPreimageRequest(ReadOnlyMemory<byte> ContentHash,
                                                  IReadOnlyList<CanonicalManifestEntry> Manifests);

/// <summary>One manifest's contribution to the collection preimage.</summary>
/// <param name="Kind">The manifest kind (its type).</param>
/// <param name="ManifestHash">The manifest's hash bytes.</param>
public sealed record CanonicalManifestEntry(string Kind,
                                            ReadOnlyMemory<byte> ManifestHash);
