namespace Xio.Parallax.Client.C2pa.Interfaces;

/// <summary>Recognises one carrier format and extracts the C2PA superbox its embedding rules place in it.</summary>
internal interface ICarrierReader
{
    /// <summary>The carrier this reader handles.</summary>
    C2paCarrier Carrier { get; }

    /// <summary>Returns whether the file starts with this carrier's signature.</summary>
    bool Recognises(ReadOnlySpan<byte> file);

    /// <summary>Extracts the candidate superbox, or null with the reason when the carrier holds none.</summary>
    /// <exception cref="C2paFormatException">The carrier's structure is malformed.</exception>
    CarrierExtraction Extract(ReadOnlyMemory<byte> file);
}
