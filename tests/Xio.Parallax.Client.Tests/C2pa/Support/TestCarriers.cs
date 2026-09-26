namespace Xio.Parallax.Client.Tests.C2pa.Support;

/// <summary>
/// Builds JUMBF stores and the carriers that embed them, byte for byte, from plain rules
/// (big-endian box and PNG lengths, little-endian RIFF and TIFF, CRC-32 over PNG type and data),
/// so the Python tests can build the same bytes.
/// </summary>
internal static class TestCarriers
{
    /// <summary>The C2PA manifest-store UUID a store's description box carries.</summary>
    internal static readonly byte[] StoreUuid = Convert.FromHexString("6332706100110010800000AA00389B71");

    /// <summary>The C2PA manifest UUID a manifest's description box carries.</summary>
    internal static readonly byte[] ManifestUuid = Convert.FromHexString("63326D6100110010800000AA00389B71");

    /// <summary>The C2PA claim UUID a claim's description box carries.</summary>
    internal static readonly byte[] ClaimUuid = Convert.FromHexString("6332636C00110010800000AA00389B71");

    private static readonly uint[] CrcTable = BuildCrcTable();

    /// <summary>A store: jumb[jumd "c2pa", jumb[jumd "urn:uuid:test-manifest", jumb[jumd "c2pa.claim", cbor]]].</summary>
    internal static byte[] SyntheticStore()
    {
        var claim = Box("jumb", Description(ClaimUuid, "c2pa.claim"), Box("cbor", [0xA1, 0x61, 0x61, 0x01]));
        var manifest = Box("jumb", Description(ManifestUuid, "urn:uuid:test-manifest"), claim);
        return Box("jumb", Description(StoreUuid, "c2pa"), manifest);
    }

    /// <summary>A store of another kind: jumb[jumd with the given UUID and label, json "{}"].</summary>
    internal static byte[] OtherStore(byte[] uuid, string label)
    {
        return Box("jumb", Description(uuid, label), Box("json", "{}"u8.ToArray()));
    }

    /// <summary>A box: its LBox (big-endian, header included), its TBox and its payload parts.</summary>
    internal static byte[] Box(string type, params byte[][] payload)
    {
        var body = payload.SelectMany(part => part).ToArray();
        var box = new byte[8 + body.Length];
        BinaryPrimitives.WriteUInt32BigEndian(box, (uint)box.Length);
        Encoding.ASCII.GetBytes(type).CopyTo(box, 4);
        body.CopyTo(box, 8);
        return box;
    }

    /// <summary>A jumd box: UUID, toggles 0x03 (requestable, labelled) and the NUL-terminated label.</summary>
    internal static byte[] Description(byte[] uuid, string label)
    {
        return Box("jumd", uuid, [0x03], Encoding.UTF8.GetBytes(label), [0x00]);
    }

    /// <summary>Splits a superbox into APP11 payloads: "JP", En, Z from 1, the superbox's LBox and TBox, then an equal share of its payload.</summary>
    internal static List<byte[]> App11Payloads(byte[] superbox, ushort instance, int count)
    {
        var header = superbox[..8];
        var body = superbox[8..];
        var share = (body.Length + count - 1) / count;
        var payloads = new List<byte[]>();
        for (var index = 0; index < count; index++)
        {
            var prefix = new byte[8];
            prefix[0] = (byte)'J';
            prefix[1] = (byte)'P';
            BinaryPrimitives.WriteUInt16BigEndian(prefix.AsSpan(2), instance);
            BinaryPrimitives.WriteUInt32BigEndian(prefix.AsSpan(4), (uint)(index + 1));
            var chunk = body.Skip(index * share).Take(share).ToArray();
            payloads.Add([.. prefix, .. header, .. chunk]);
        }

        return payloads;
    }

    /// <summary>A JPEG: SOI, a JFIF APP0, one APP11 segment per payload in the given order, an SOS stub with two scan bytes, EOI.</summary>
    internal static byte[] Jpeg(IEnumerable<byte[]> app11Payloads)
    {
        byte[] jfif = [0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00];
        List<byte> file = [0xFF, 0xD8, .. Segment(0xE0, jfif)];
        foreach (var payload in app11Payloads)
        {
            file.AddRange(Segment(0xEB, payload));
        }

        file.AddRange(Segment(0xDA, [0x01, 0x01, 0x00, 0x00, 0x3F, 0x00]));
        file.AddRange([0x12, 0x34, 0xFF, 0xD9]);
        return [.. file];
    }

    /// <summary>A PNG: the signature, a 1x1 IHDR, the given chunks and IEND, each with its CRC-32.</summary>
    internal static byte[] Png(params (string Type, byte[] Data)[] chunks)
    {
        byte[] ihdr = [0, 0, 0, 1, 0, 0, 0, 1, 8, 2, 0, 0, 0];
        List<byte> file = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, .. PngChunk("IHDR", ihdr)];
        foreach (var (type, data) in chunks)
        {
            file.AddRange(PngChunk(type, data));
        }

        file.AddRange(PngChunk("IEND", []));
        return [.. file];
    }

    /// <summary>A WebP: RIFF, its little-endian size, WEBP, a VP8L stub chunk and a C2PA chunk, each padded to an even length.</summary>
    internal static byte[] WebP(byte[] c2paData)
    {
        List<byte> body = [.. "WEBP"u8.ToArray(), .. RiffChunk("VP8L", [0x2F, 0x00, 0x00, 0x00, 0x00]), .. RiffChunk("C2PA", c2paData)];
        var size = new byte[4];
        BinaryPrimitives.WriteUInt32LittleEndian(size, (uint)body.Count);
        return [.. "RIFF"u8.ToArray(), .. size, .. body];
    }

    /// <summary>A little-endian TIFF whose single IFD holds tag 52545 (UNDEFINED) pointing at the data after the IFD.</summary>
    internal static byte[] Tiff(byte[] c2paData)
    {
        var header = new byte[8 + 2 + 12 + 4];
        "II*\0"u8.CopyTo(header);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(4), 8);
        BinaryPrimitives.WriteUInt16LittleEndian(header.AsSpan(8), 1);
        BinaryPrimitives.WriteUInt16LittleEndian(header.AsSpan(10), 0xCD41);
        BinaryPrimitives.WriteUInt16LittleEndian(header.AsSpan(12), 7);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(14), (uint)c2paData.Length);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(18), (uint)header.Length);
        return [.. header, .. c2paData];
    }

    /// <summary>A GIF89a header and trailer.</summary>
    internal static byte[] Gif()
    {
        return [.. "GIF89a"u8.ToArray(), 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x3B];
    }

    private static byte[] Segment(byte marker, byte[] payload)
    {
        var segment = new byte[4 + payload.Length];
        segment[0] = 0xFF;
        segment[1] = marker;
        BinaryPrimitives.WriteUInt16BigEndian(segment.AsSpan(2), (ushort)(payload.Length + 2));
        payload.CopyTo(segment, 4);
        return segment;
    }

    private static byte[] PngChunk(string type, byte[] data)
    {
        var typed = Encoding.ASCII.GetBytes(type).Concat(data).ToArray();
        var chunk = new byte[4 + typed.Length + 4];
        BinaryPrimitives.WriteUInt32BigEndian(chunk, (uint)data.Length);
        typed.CopyTo(chunk, 4);
        BinaryPrimitives.WriteUInt32BigEndian(chunk.AsSpan(4 + typed.Length), Crc32(typed));
        return chunk;
    }

    private static byte[] RiffChunk(string fourCc, byte[] data)
    {
        var size = new byte[4];
        BinaryPrimitives.WriteUInt32LittleEndian(size, (uint)data.Length);
        byte[] padding = data.Length % 2 == 1 ? [0x00] : [];
        return [.. Encoding.ASCII.GetBytes(fourCc), .. size, .. data, .. padding];
    }

    private static uint Crc32(byte[] bytes)
    {
        var crc = 0xFFFFFFFFu;
        foreach (var value in bytes)
        {
            crc = CrcTable[(crc ^ value) & 0xFF] ^ (crc >> 8);
        }

        return crc ^ 0xFFFFFFFFu;
    }

    private static uint[] BuildCrcTable()
    {
        var table = new uint[256];
        for (var index = 0u; index < 256; index++)
        {
            var value = index;
            for (var bit = 0; bit < 8; bit++)
            {
                value = (value & 1) != 0 ? 0xEDB88320u ^ (value >> 1) : value >> 1;
            }

            table[index] = value;
        }

        return table;
    }
}
