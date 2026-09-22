namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Extracts a C2PA store from a PNG's caBX chunk, whose data is the whole superbox.</summary>
internal sealed class PngCarrierReader : ICarrierReader
{
    private const int ChunkHeaderLength = 8;
    private const int ChunkCrcLength = 4;

    public C2paCarrier Carrier => C2paCarrier.Png;

    public bool Recognises(ReadOnlySpan<byte> file)
    {
        return file.StartsWith(C2paConstants.PngSignature);
    }

    public CarrierExtraction Extract(ReadOnlyMemory<byte> file)
    {
        var span = file.Span;
        var offset = C2paConstants.PngSignature.Length;
        ReadOnlyMemory<byte>? store = null;
        while (offset < span.Length)
        {
            if (span.Length - offset < ChunkHeaderLength + ChunkCrcLength)
            {
                throw new C2paFormatException($"The PNG chunk at offset {offset} is truncated.");
            }

            var length = BinaryPrimitives.ReadUInt32BigEndian(span[offset..]);
            var type = Encoding.Latin1.GetString(span.Slice(offset + 4, 4));
            if (length > (uint)(span.Length - offset - ChunkHeaderLength - ChunkCrcLength))
            {
                throw new C2paFormatException($"The PNG '{type}' chunk at offset {offset} declares {length} bytes, which does not fit the file.");
            }

            if (type == C2paConstants.PngStoreChunk)
            {
                if (store is not null)
                {
                    throw new C2paFormatException("The PNG carries more than one caBX chunk; exactly one is expected.");
                }

                store = file.Slice(offset + ChunkHeaderLength, (int)length);
            }

            if (type == C2paConstants.PngEndChunk)
            {
                break;
            }

            offset += ChunkHeaderLength + (int)length + ChunkCrcLength;
        }

        return store is null
            ? new CarrierExtraction(null, "The PNG carries no caBX chunk, so no C2PA store.")
            : new CarrierExtraction(store, "A C2PA store from the PNG's caBX chunk.");
    }
}
