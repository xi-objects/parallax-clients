namespace Xio.Parallax.Client.C2pa.Interfaces;

/// <summary>Reads JUMBF box headers and validates a superbox as a C2PA manifest store.</summary>
internal interface IJumbfStoreReader
{
    /// <summary>Reads the box header at the offset, within a buffer that ends at the limit.</summary>
    /// <exception cref="C2paFormatException">The header is truncated or its length overruns the limit.</exception>
    JumbfBoxHeader ReadHeader(ReadOnlySpan<byte> buffer, int offset, int limit);

    /// <summary>Returns whether the bytes are one well-formed jumb box whose description box carries the C2PA manifest-store UUID.</summary>
    bool IsC2paStore(ReadOnlySpan<byte> superbox);

    /// <summary>Validates the bytes as one C2PA manifest store spanning the whole buffer and summarises every box in it.</summary>
    /// <exception cref="C2paFormatException">The bytes are not one well-formed jumb box, or not a C2PA manifest store.</exception>
    IReadOnlyList<JumbfBoxSummary> Summarise(ReadOnlySpan<byte> superbox);
}
