namespace Xio.Parallax.Client.Verification.Interfaces;

/// <summary>Builds the version-2 canonical preimages a published record's Ed25519 signatures are made over; every length prefix is a big-endian uint16.</summary>
public interface ICanonicalPreimageBuilder
{
    /// <summary>Builds the per-manifest preimage: <c>[0x02] ‖ len‖contentHash ‖ len‖kind(utf-8) ‖ len‖manifestHash</c>.</summary>
    byte[] Manifest(XioManifestPreimageRequest request);

    /// <summary>Builds the collection preimage: <c>[0x02] ‖ len‖contentHash ‖ count(uint16) ‖ for each manifest in record order: len‖kind(utf-8) ‖ len‖manifestHash</c>.</summary>
    byte[] Collection(XioCollectionPreimageRequest request);

    /// <summary>Builds the image (content-hash) preimage: the content hash bytes alone, with no framing.</summary>
    /// <returns>A copy of the content hash bytes.</returns>
    byte[] Image(ReadOnlyMemory<byte> contentHash);
}
