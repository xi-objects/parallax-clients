namespace Xio.Parallax.Client.C2pa.Interfaces;

/// <summary>Reads JUMBF box headers, walks a superbox as a JUMBF manifest store and classifies it c2pa or jumbf.</summary>
internal interface IJumbfStoreReader
{
    /// <summary>Reads the box header at the offset, within a buffer that ends at the limit.</summary>
    /// <exception cref="C2paFormatException">The header is truncated or its length overruns the limit.</exception>
    JumbfBoxHeader ReadHeader(ReadOnlySpan<byte> buffer, int offset, int limit);

    /// <summary>Walks the bytes as one well-formed jumb superbox spanning the whole buffer and summarises every box in it.</summary>
    /// <exception cref="C2paFormatException">The bytes are not one well-formed jumb superbox.</exception>
    IReadOnlyList<JumbfBoxSummary> Summarise(ReadOnlySpan<byte> superbox);

    /// <summary>Classifies a well-formed superbox: c2pa when its description box carries the C2PA manifest-store UUID and the label c2pa, else jumbf.</summary>
    /// <exception cref="C2paFormatException">The bytes are not one well-formed jumb superbox.</exception>
    string Classify(ReadOnlySpan<byte> superbox);
}
