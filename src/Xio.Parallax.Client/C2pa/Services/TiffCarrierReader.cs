namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Extracts the JUMBF manifest store from tag 52545 (UNDEFINED) of a classic TIFF's top-level IFD chain, which also covers DNG.</summary>
internal sealed class TiffCarrierReader : ICarrierReader
{
    private const int HeaderLength = 8;
    private const int EntryLength = 12;
    private const int InlineValueLength = 4;

    public C2paCarrier Carrier => C2paCarrier.Tiff;

    public bool Recognises(ReadOnlySpan<byte> file)
    {
        return file.StartsWith(C2paConstants.TiffLittleEndian) || file.StartsWith(C2paConstants.TiffBigEndian);
    }

    public CarrierExtraction Extract(ReadOnlyMemory<byte> file)
    {
        var span = file.Span;
        var littleEndian = span.StartsWith(C2paConstants.TiffLittleEndian);
        if (span.Length < HeaderLength)
        {
            throw new C2paFormatException("The TIFF header is truncated.");
        }

        var ifd = ReadUInt32(span, 4, littleEndian);
        var visited = new HashSet<uint>();
        ReadOnlyMemory<byte>? store = null;
        while (ifd != 0)
        {
            if (!visited.Add(ifd) || visited.Count > C2paConstants.TiffMaxIfds)
            {
                throw new C2paFormatException("The TIFF's IFD chain loops or is longer than the reader accepts.");
            }

            var found = ReadIfd(file, ifd, littleEndian, out ifd);
            if (found is not null && store is not null)
            {
                throw new C2paFormatException("The TIFF carries tag 52545 more than once; exactly one is expected.");
            }

            store ??= found;
        }

        return store is null
            ? new CarrierExtraction([], "The TIFF carries no tag 52545, so no embedded manifest store.")
            : new CarrierExtraction([store.Value], "A JUMBF manifest store from the TIFF's tag 52545.");
    }

    private static ReadOnlyMemory<byte>? ReadIfd(ReadOnlyMemory<byte> file, uint ifd, bool littleEndian, out uint next)
    {
        var span = file.Span;
        if (ifd > (uint)(span.Length - 2))
        {
            throw new C2paFormatException($"The TIFF IFD offset {ifd} lies outside the file.");
        }

        var start = (int)ifd;
        var count = ReadUInt16(span, start, littleEndian);
        var entriesEnd = (long)start + 2 + ((long)count * EntryLength);
        if (entriesEnd + 4 > span.Length)
        {
            throw new C2paFormatException($"The TIFF IFD at offset {ifd} is truncated.");
        }

        ReadOnlyMemory<byte>? store = null;
        for (var entry = start + 2; entry < entriesEnd; entry += EntryLength)
        {
            if (ReadUInt16(span, entry, littleEndian) != C2paConstants.TiffStoreTag)
            {
                continue;
            }

            if (ReadUInt16(span, entry + 2, littleEndian) != C2paConstants.TiffUndefinedType)
            {
                throw new C2paFormatException("The TIFF's tag 52545 is not of type UNDEFINED.");
            }

            var length = ReadUInt32(span, entry + 4, littleEndian);
            var valueOffset = length <= InlineValueLength ? (uint)(entry + 8) : ReadUInt32(span, entry + 8, littleEndian);
            if ((ulong)valueOffset + length > (ulong)span.Length)
            {
                throw new C2paFormatException($"The TIFF's tag 52545 declares {length} bytes at offset {valueOffset}, which does not fit the file.");
            }

            store = file.Slice((int)valueOffset, (int)length);
        }

        next = ReadUInt32(span, (int)entriesEnd, littleEndian);
        return store;
    }

    private static ushort ReadUInt16(ReadOnlySpan<byte> span, int offset, bool littleEndian)
    {
        return littleEndian
            ? BinaryPrimitives.ReadUInt16LittleEndian(span[offset..])
            : BinaryPrimitives.ReadUInt16BigEndian(span[offset..]);
    }

    private static uint ReadUInt32(ReadOnlySpan<byte> span, int offset, bool littleEndian)
    {
        return littleEndian
            ? BinaryPrimitives.ReadUInt32LittleEndian(span[offset..])
            : BinaryPrimitives.ReadUInt32BigEndian(span[offset..]);
    }
}
