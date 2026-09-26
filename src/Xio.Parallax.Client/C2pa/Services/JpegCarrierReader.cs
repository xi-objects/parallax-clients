namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Reassembles every jumb box instance (other box types, such as JPEG XT's, are ignored) from a JPEG's APP11 segments, in document order: each segment carries "JP", En, Z, the superbox's LBox and TBox, and a chunk of its payload.</summary>
internal sealed class JpegCarrierReader : ICarrierReader
{
    private const int SegmentHeaderLength = 8;
    private const int BoxHeaderLength = 8;
    private const int ExtendedBoxHeaderLength = 16;

    private static readonly byte[] SuperboxType = Encoding.Latin1.GetBytes(C2paConstants.SuperboxType);

    public C2paCarrier Carrier => C2paCarrier.Jpeg;

    public bool Recognises(ReadOnlySpan<byte> file)
    {
        return file.StartsWith(C2paConstants.JpegSignature);
    }

    public CarrierExtraction Extract(ReadOnlyMemory<byte> file)
    {
        var groups = new Dictionary<ushort, JpegBoxGroup>();
        var order = new List<JpegBoxGroup>();
        foreach (var payload in App11Payloads(file))
        {
            Collect(file.Span.Slice(payload.Start, payload.Length), payload.Start, groups, order);
        }

        if (groups.Count == 0)
        {
            return new CarrierExtraction([], "The JPEG carries no jumb box instance in APP11, so no embedded manifest store.");
        }

        var superboxes = order
            .Select(group => (ReadOnlyMemory<byte>)group.Reassemble(file.Span))
            .ToList();
        return new CarrierExtraction(superboxes, $"{superboxes.Count} JUMBF box instance(s) reassembled from APP11 segments.");
    }

    private static List<(int Start, int Length)> App11Payloads(ReadOnlyMemory<byte> file)
    {
        var span = file.Span;
        var payloads = new List<(int Start, int Length)>();
        var offset = 2;
        while (offset < span.Length)
        {
            if (span[offset] != C2paConstants.JpegMarkerPrefix)
            {
                throw new C2paFormatException($"The JPEG has no marker at offset {offset}.");
            }

            while (offset < span.Length && span[offset] == C2paConstants.JpegMarkerPrefix)
            {
                offset++;
            }

            if (offset >= span.Length)
            {
                break;
            }

            var marker = span[offset++];
            if (marker == C2paConstants.JpegStartOfScan || marker == C2paConstants.JpegEndOfImage)
            {
                break;
            }

            if (marker == 0x01 || (marker >= 0xD0 && marker <= 0xD7))
            {
                continue;
            }

            if (span.Length - offset < 2)
            {
                throw new C2paFormatException($"The JPEG segment 0xFF{marker:X2} at offset {offset - 2} is truncated.");
            }

            var length = BinaryPrimitives.ReadUInt16BigEndian(span[offset..]);
            if (length < 2 || length > span.Length - offset)
            {
                throw new C2paFormatException($"The JPEG segment 0xFF{marker:X2} at offset {offset - 2} declares {length} bytes, which does not fit the file.");
            }

            if (marker == C2paConstants.JpegApp11)
            {
                payloads.Add((offset + 2, length - 2));
            }

            offset += length;
        }

        return payloads;
    }

    private static void Collect(ReadOnlySpan<byte> payload, int start, Dictionary<ushort, JpegBoxGroup> groups, List<JpegBoxGroup> order)
    {
        if (!payload.StartsWith(C2paConstants.JpegApp11Magic))
        {
            return;
        }

        if (payload.Length < SegmentHeaderLength + BoxHeaderLength)
        {
            throw new C2paFormatException($"The JUMBF APP11 segment at offset {start} is shorter than its headers.");
        }

        var instance = BinaryPrimitives.ReadUInt16BigEndian(payload[2..]);
        var sequence = BinaryPrimitives.ReadUInt32BigEndian(payload[4..]);
        var box = payload[SegmentHeaderLength..];
        if (!box.Slice(4, 4).SequenceEqual(SuperboxType))
        {
            return;
        }

        var headerLength = BinaryPrimitives.ReadUInt32BigEndian(box) == 1 ? ExtendedBoxHeaderLength : BoxHeaderLength;
        if (box.Length < headerLength)
        {
            throw new C2paFormatException($"The JUMBF APP11 segment at offset {start} is shorter than its box header.");
        }

        if (!groups.TryGetValue(instance, out var group))
        {
            group = new JpegBoxGroup(instance, box[..headerLength].ToArray());
            groups.Add(instance, group);
            order.Add(group);
        }

        group.Add(sequence, box[..headerLength], (start + SegmentHeaderLength + headerLength, box.Length - headerLength));
    }

    /// <summary>The APP11 segments of one box instance: the header they share and their chunks by sequence number.</summary>
    private sealed class JpegBoxGroup(ushort _instance, byte[] _header)
    {
        private readonly SortedDictionary<uint, (int Start, int Length)> _chunks = [];

        public void Add(uint sequence, ReadOnlySpan<byte> header, (int Start, int Length) chunk)
        {
            if (!header.SequenceEqual(_header))
            {
                throw new C2paFormatException($"The APP11 segments of box instance {_instance} do not repeat the same LBox and TBox.");
            }

            if (!_chunks.TryAdd(sequence, chunk))
            {
                throw new C2paFormatException($"Box instance {_instance} repeats packet sequence number {sequence}.");
            }
        }

        public byte[] Reassemble(ReadOnlySpan<byte> file)
        {
            var sequences = _chunks.Keys.ToList();
            if (sequences[^1] - sequences[0] != (uint)(sequences.Count - 1))
            {
                throw new C2paFormatException($"Box instance {_instance} is missing a packet: its sequence numbers are not consecutive.");
            }

            var buffer = new List<byte>(_header);
            foreach (var chunk in _chunks.Values)
            {
                buffer.AddRange(file.Slice(chunk.Start, chunk.Length));
            }

            return [.. buffer];
        }
    }
}
