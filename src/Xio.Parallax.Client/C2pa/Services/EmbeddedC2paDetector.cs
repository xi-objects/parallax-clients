namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Detects an embedded C2PA manifest store in JPEG (APP11), PNG (caBX), WebP (C2PA chunk) and TIFF or DNG (tag 52545) files; any other file is reported as unsupported.</summary>
public sealed class EmbeddedC2paDetector : IEmbeddedC2paDetector
{
    private readonly IReadOnlyList<ICarrierReader> _readers;
    private readonly IJumbfStoreReader _jumbf;

    /// <summary>Creates the detector over the built-in carrier readers.</summary>
    public EmbeddedC2paDetector()
        : this(C2paComposition.CarrierReaders, C2paComposition.JumbfReader)
    {
    }

    internal EmbeddedC2paDetector(IReadOnlyList<ICarrierReader> readers,
                                  IJumbfStoreReader jumbf)
    {
        _readers = readers;
        _jumbf = jumbf;
    }

    /// <inheritdoc/>
    public EmbeddedC2paResult Detect(ReadOnlyMemory<byte> file)
    {
        var reader = _readers.FirstOrDefault(candidate => candidate.Recognises(file.Span));
        if (reader is null)
        {
            return new EmbeddedC2paResult(C2paCarrier.Unsupported, null, "The file's signature is not JPEG, PNG, WebP or TIFF, so whether it carries C2PA is not determined.");
        }

        try
        {
            var extraction = reader.Extract(file);
            if (extraction.Superbox is not { } superbox)
            {
                return new EmbeddedC2paResult(reader.Carrier, null, extraction.Detail);
            }

            var boxes = _jumbf.Summarise(superbox.Span);
            return new EmbeddedC2paResult(reader.Carrier, new EmbeddedC2paStore(superbox.ToArray(), boxes), $"{extraction.Detail} {superbox.Length} bytes in {boxes.Count} boxes.");
        }
        catch (C2paFormatException exception)
        {
            return new EmbeddedC2paResult(reader.Carrier, null, $"Malformed {reader.Carrier} C2PA embedding: {exception.Message}");
        }
    }
}
