namespace Xio.Parallax.Client.C2pa.Services;

/// <summary>Detects every embedded JUMBF manifest store in JPEG (APP11), PNG (caBX), WebP (C2PA chunk) and TIFF or DNG (tag 52545) files and classifies each c2pa or jumbf; any other file is reported as unsupported.</summary>
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
            return new EmbeddedC2paResult(C2paCarrier.Unsupported, EmbeddedC2paOutcome.Unsupported, [], "The file's signature is not JPEG, PNG, WebP or TIFF, so whether it carries an embedded manifest store is not determined.");
        }

        try
        {
            var extraction = reader.Extract(file);
            if (extraction.Superboxes.Count == 0)
            {
                return new EmbeddedC2paResult(reader.Carrier, EmbeddedC2paOutcome.Absent, [], extraction.Detail);
            }

            var stores = extraction.Superboxes.Select(Store).ToList();
            var repeated = stores.GroupBy(store => store.Kind).FirstOrDefault(group => group.Count() > 1);
            if (repeated is not null)
            {
                return new EmbeddedC2paResult(reader.Carrier, EmbeddedC2paOutcome.Malformed, [], $"Malformed {reader.Carrier} embedding: it carries {repeated.Count()} manifest stores of kind '{repeated.Key}'; one kind carries one manifest.");
            }

            var kinds = string.Join(", ", stores.Select(store => $"{store.Kind} ({store.Bytes.Length} bytes in {store.Boxes.Count} boxes)"));
            return new EmbeddedC2paResult(reader.Carrier, EmbeddedC2paOutcome.Found, stores, $"{extraction.Detail} Stores: {kinds}.");
        }
        catch (C2paFormatException exception)
        {
            return new EmbeddedC2paResult(reader.Carrier, EmbeddedC2paOutcome.Malformed, [], $"Malformed {reader.Carrier} embedding: {exception.Message}");
        }
    }

    private EmbeddedC2paStore Store(ReadOnlyMemory<byte> superbox)
    {
        var boxes = _jumbf.Summarise(superbox.Span);
        return new EmbeddedC2paStore(_jumbf.Classify(superbox.Span), superbox.ToArray(), boxes);
    }
}
