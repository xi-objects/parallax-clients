namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Reads JUMBF (ISO/IEC 19566-5) box headers and walks a JUMBF manifest store's box tree without parsing its contents, and classifies it c2pa or jumbf.</summary>
internal sealed class JumbfStoreReader : IJumbfStoreReader
{
    private const int BasicHeaderLength = 8;
    private const int ExtendedHeaderLength = 16;
    private const uint ExtendedLengthMarker = 1;
    private const uint ToEndMarker = 0;

    public JumbfBoxHeader ReadHeader(ReadOnlySpan<byte> buffer, int offset, int limit)
    {
        if (limit - offset < BasicHeaderLength)
        {
            throw new C2paFormatException($"A JUMBF box header at offset {offset} is truncated.");
        }

        var declared = BinaryPrimitives.ReadUInt32BigEndian(buffer[offset..]);
        var type = Encoding.Latin1.GetString(buffer.Slice(offset + 4, 4));
        if (declared == ToEndMarker)
        {
            return new JumbfBoxHeader(type, offset, offset + BasicHeaderLength, limit);
        }

        if (declared == ExtendedLengthMarker)
        {
            if (limit - offset < ExtendedHeaderLength)
            {
                throw new C2paFormatException($"The '{type}' box at offset {offset} declares an XLBox but is truncated.");
            }

            var extended = BinaryPrimitives.ReadUInt64BigEndian(buffer[(offset + BasicHeaderLength)..]);
            return new JumbfBoxHeader(type, offset, offset + ExtendedHeaderLength, End(type, offset, limit, extended, ExtendedHeaderLength));
        }

        return new JumbfBoxHeader(type, offset, offset + BasicHeaderLength, End(type, offset, limit, declared, BasicHeaderLength));
    }

    public IReadOnlyList<JumbfBoxSummary> Summarise(ReadOnlySpan<byte> superbox)
    {
        var header = ReadSuperbox(superbox);
        var boxes = new List<JumbfBoxSummary>();
        Walk(superbox, header, 0, boxes);
        return boxes;
    }

    public string Classify(ReadOnlySpan<byte> superbox)
    {
        var header = ReadSuperbox(superbox);
        var description = ReadHeader(superbox, header.PayloadStart, header.End);
        if (description.Type != C2paConstants.DescriptionType)
        {
            throw new C2paFormatException($"The jumb box at offset {header.Start} opens with a '{description.Type}' box, not a jumd description box.");
        }

        var payload = superbox[description.PayloadStart..description.End];
        var carriesStoreUuid = payload.Length >= C2paConstants.JumdUuidLength
            && payload[..C2paConstants.JumdUuidLength].SequenceEqual(C2paConstants.C2paStoreUuid);
        return carriesStoreUuid && ReadLabel(payload, description.Start) == C2paConstants.C2paStoreLabel
            ? C2paConstants.C2paKind
            : C2paConstants.JumbfKind;
    }

    private JumbfBoxHeader ReadSuperbox(ReadOnlySpan<byte> superbox)
    {
        var header = ReadHeader(superbox, 0, superbox.Length);
        if (header.Type != C2paConstants.SuperboxType)
        {
            throw new C2paFormatException($"The embedded bytes are a '{header.Type}' box, not a jumb superbox.");
        }

        if (header.End != superbox.Length)
        {
            throw new C2paFormatException($"The jumb superbox declares {header.End} bytes but {superbox.Length} were embedded.");
        }

        return header;
    }

    private static int End(string type, int offset, int limit, ulong declared, int headerLength)
    {
        if (declared < (ulong)headerLength || declared > (ulong)(limit - offset))
        {
            throw new C2paFormatException($"The '{type}' box at offset {offset} declares {declared} bytes, which does not fit the {limit - offset} available.");
        }

        return offset + (int)declared;
    }

    private void Walk(ReadOnlySpan<byte> buffer, JumbfBoxHeader box, int depth, List<JumbfBoxSummary> boxes)
    {
        if (depth > C2paConstants.MaxBoxDepth)
        {
            throw new C2paFormatException($"The store nests boxes deeper than {C2paConstants.MaxBoxDepth} levels.");
        }

        if (box.Type != C2paConstants.SuperboxType)
        {
            boxes.Add(new JumbfBoxSummary(box.Type, null, depth, box.End - box.Start));
            return;
        }

        var description = ReadHeader(buffer, box.PayloadStart, box.End);
        if (description.Type != C2paConstants.DescriptionType)
        {
            throw new C2paFormatException($"The jumb box at offset {box.Start} opens with a '{description.Type}' box, not a jumd description box.");
        }

        var label = ReadLabel(buffer[description.PayloadStart..description.End], description.Start);
        boxes.Add(new JumbfBoxSummary(box.Type, label, depth, box.End - box.Start));
        boxes.Add(new JumbfBoxSummary(description.Type, label, depth + 1, description.End - description.Start));
        var offset = description.End;
        while (offset < box.End)
        {
            var child = ReadHeader(buffer, offset, box.End);
            Walk(buffer, child, depth + 1, boxes);
            offset = child.End;
        }
    }

    private static string? ReadLabel(ReadOnlySpan<byte> payload, int offset)
    {
        if (payload.Length <= C2paConstants.JumdUuidLength)
        {
            throw new C2paFormatException($"The jumd box at offset {offset} is shorter than its UUID and toggles.");
        }

        var toggles = payload[C2paConstants.JumdUuidLength];
        if ((toggles & C2paConstants.LabelToggle) == 0)
        {
            return null;
        }

        var text = payload[(C2paConstants.JumdUuidLength + 1)..];
        var terminator = text.IndexOf((byte)0);
        if (terminator < 0)
        {
            throw new C2paFormatException($"The jumd box at offset {offset} declares a label with no NUL terminator.");
        }

        return Encoding.UTF8.GetString(text[..terminator]);
    }
}
