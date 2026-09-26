namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Extracts the JUMBF manifest store from a WebP's RIFF chunk with FourCC C2PA, whose data is the whole superbox.</summary>
internal sealed class WebPCarrierReader : ICarrierReader
{
    private const int RiffHeaderLength = 12;
    private const int ChunkHeaderLength = 8;

    public C2paCarrier Carrier => C2paCarrier.WebP;

    public bool Recognises(ReadOnlySpan<byte> file)
    {
        return file.Length >= RiffHeaderLength
            && file.StartsWith(C2paConstants.RiffMagic)
            && file.Slice(8, 4).SequenceEqual(C2paConstants.WebPMagic);
    }

    public CarrierExtraction Extract(ReadOnlyMemory<byte> file)
    {
        var span = file.Span;
        var riffSize = BinaryPrimitives.ReadUInt32LittleEndian(span[4..]);
        if (riffSize > (uint)(span.Length - 8))
        {
            throw new C2paFormatException($"The RIFF header declares {riffSize} bytes, which does not fit the file.");
        }

        var end = 8 + (int)riffSize;
        var offset = RiffHeaderLength;
        ReadOnlyMemory<byte>? store = null;
        while (offset < end)
        {
            if (end - offset < ChunkHeaderLength)
            {
                throw new C2paFormatException($"The RIFF chunk at offset {offset} is truncated.");
            }

            var fourCc = Encoding.Latin1.GetString(span.Slice(offset, 4));
            var length = BinaryPrimitives.ReadUInt32LittleEndian(span[(offset + 4)..]);
            if (length > (uint)(end - offset - ChunkHeaderLength))
            {
                throw new C2paFormatException($"The RIFF '{fourCc}' chunk at offset {offset} declares {length} bytes, which does not fit the file.");
            }

            if (fourCc == C2paConstants.WebPStoreChunk)
            {
                if (store is not null)
                {
                    throw new C2paFormatException("The WebP carries more than one C2PA chunk; exactly one is expected.");
                }

                store = file.Slice(offset + ChunkHeaderLength, (int)length);
            }

            offset += ChunkHeaderLength + (int)length + (int)(length & 1);
        }

        return store is null
            ? new CarrierExtraction([], "The WebP carries no C2PA chunk, so no embedded manifest store.")
            : new CarrierExtraction([store.Value], "A JUMBF manifest store from the WebP's C2PA chunk.");
    }
}
