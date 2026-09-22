namespace Xio.Parallax.Client.Verification.Services;

/// <summary>Builds the version-2 canonical preimages with the <see cref="VerificationConstants.ImplementedCanonicalVersion"/> byte and big-endian uint16 length prefixes.</summary>
public sealed class CanonicalPreimageBuilder : ICanonicalPreimageBuilder
{
    /// <inheritdoc/>
    public byte[] Manifest(XioManifestPreimageRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(request.Kind);
        using var buffer = new MemoryStream();
        buffer.WriteByte(VerificationConstants.ImplementedCanonicalVersion);
        WritePrefixed(buffer, request.ContentHash.Span);
        WritePrefixed(buffer, Encoding.UTF8.GetBytes(request.Kind));
        WritePrefixed(buffer, request.ManifestHash.Span);
        return buffer.ToArray();
    }

    /// <inheritdoc/>
    public byte[] Collection(XioCollectionPreimageRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        var manifests = request.Manifests;
        ArgumentNullException.ThrowIfNull(manifests, nameof(request.Manifests));
        if (manifests.Count > ushort.MaxValue)
        {
            throw new ArgumentOutOfRangeException(nameof(request), manifests.Count, "The collection preimage carries at most 65535 manifests.");
        }

        using var buffer = new MemoryStream();
        buffer.WriteByte(VerificationConstants.ImplementedCanonicalVersion);
        WritePrefixed(buffer, request.ContentHash.Span);
        WriteUInt16(buffer, manifests.Count);
        foreach (var entry in manifests)
        {
            ArgumentNullException.ThrowIfNull(entry);
            ArgumentNullException.ThrowIfNull(entry.Kind);
            WritePrefixed(buffer, Encoding.UTF8.GetBytes(entry.Kind));
            WritePrefixed(buffer, entry.ManifestHash.Span);
        }

        return buffer.ToArray();
    }

    /// <inheritdoc/>
    public byte[] Image(ReadOnlyMemory<byte> contentHash)
    {
        return contentHash.ToArray();
    }

    private static void WritePrefixed(MemoryStream buffer, ReadOnlySpan<byte> value)
    {
        if (value.Length > ushort.MaxValue)
        {
            throw new ArgumentOutOfRangeException(nameof(value), value.Length, "A length-prefixed field carries at most 65535 bytes.");
        }

        WriteUInt16(buffer, value.Length);
        buffer.Write(value);
    }

    private static void WriteUInt16(MemoryStream buffer, int value)
    {
        Span<byte> prefix = stackalloc byte[2];
        BinaryPrimitives.WriteUInt16BigEndian(prefix, (ushort)value);
        buffer.Write(prefix);
    }
}
