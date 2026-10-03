namespace Xio.Parallax.Client.Tests.Verification.Services;

// PC-119: the .NET verifier's preimage and sequence hash against xio_parallax_common's own vectors - generated
// independently of every library, vendored unmodified under python/tests/vectors/px-frame (VECTORS.md names the
// commit) - so this client and Common lay out the same bytes, whatever either one's code says
public sealed class SequenceSummaryVectorConformanceTests
{
    private readonly ISequenceSummaryPreimageBuilder _builder = new SequenceSummaryPreimageBuilder();

    public static TheoryData<string> SummaryVectors() => VectorNames("sequence-summary");

    public static TheoryData<string> SequenceHashVectors() => VectorNames("sequence-hash");

    [Theory]
    [MemberData(nameof(SummaryVectors))]
    public void Every_summary_vector_lays_out_byte_for_byte(string name)
    {
        var vector = Read("sequence-summary", name);
        var verdict = vector.GetProperty("verdict");
        var frames = vector.GetProperty("frames").EnumerateArray()
            .Select(frame => new SequenceSummaryFrameEntry(
                long.Parse(frame.GetProperty("frameId").GetString()!, CultureInfo.InvariantCulture),
                Convert.FromHexString(frame.GetProperty("originalImageHash").GetString()!),
                Convert.FromHexString(frame.GetProperty("frameHash").GetString()!)))
            .ToArray();
        var expected = vector.GetProperty("expectedSize");

        var request = new XioSequenceSummaryPreimageRequest(
            Convert.FromHexString(vector.GetProperty("sequenceHash").GetString()!),
            expected.ValueKind == JsonValueKind.Null ? null : expected.GetInt32(),
            vector.GetProperty("finalSize").GetInt32(),
            verdict.GetProperty("connected").GetBoolean(),
            verdict.GetProperty("sealed").GetBoolean(),
            long.Parse(verdict.GetProperty("reach").GetString()!, CultureInfo.InvariantCulture),
            verdict.GetProperty("framesReceived").GetInt32(),
            frames);

        Assert.Equal(vector.GetProperty("framesDigest").GetString(), Convert.ToHexStringLower(_builder.FramesDigest(frames)));
        Assert.Equal(vector.GetProperty("preimage").GetString(), Convert.ToHexStringLower(_builder.Build(request)));
    }

    [Theory]
    [MemberData(nameof(SequenceHashVectors))]
    public void Every_sequence_hash_vector_recomputes_through_the_checker(string name)
    {
        var vector = Read("sequence-hash", name);
        var frames = vector.GetProperty("bodyFrameHashesInWalkOrder").EnumerateArray()
            .Select((hash, index) => new PublishedSequenceFrame { FrameId = index + 1, OriginalImageHash = new string('0', 64), FrameHash = hash.GetString() })
            .ToList();
        var checker = new SequenceSummaryChecker(new VerificationEncoding(), _builder, new SignatureChecker(new VerificationEncoding()));

        var checks = checker.Check(new XioSequenceSummaryCheckRequest(
            new PublishedSequence { Frames = frames },
            new RecordAdmissionResult(Convert.FromHexString(vector.GetProperty("sequenceHash").GetString()!), null, false)));

        Assert.Equal(VerificationOutcome.Passed, checks.Single(c => c.Name == "sequenceHash").Outcome);
    }

    private static TheoryData<string> VectorNames(string folder)
    {
        var names = new TheoryData<string>();
        foreach (var path in Directory.EnumerateFiles(Path.Combine(VectorsRoot(), folder), "*.json").Order(StringComparer.Ordinal))
        {
            names.Add(Path.GetFileName(path));
        }

        return names;
    }

    private static JsonElement Read(string folder, string name)
    {
        using var document = JsonDocument.Parse(File.ReadAllBytes(Path.Combine(VectorsRoot(), folder, name)));
        return document.RootElement.Clone();
    }

    // PC-119: the one vendored copy, shared with the Python conformance suite, found from the repository root
    private static string VectorsRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "Xio.Parallax.Client.slnx")))
        {
            directory = directory.Parent;
        }

        return Path.Combine(directory?.FullName ?? throw new DirectoryNotFoundException("The repository root holding Xio.Parallax.Client.slnx was not found."),
                            "python", "tests", "vectors", "px-frame");
    }
}
