// PC-105: the stand-in for the ingestion that comes later - a directory of image files as one
// sequence's frame source, registered through the one-call conversation, then a round-trip
// look-up of its first image. Proves ISequenceFrameSource is enough for a real registration.
//
// Environment:
//   PARALLAX_BASE_URL                the API's base URL (defaults to https://api.parallax.xiobjects.com)
//   PARALLAX_TOKEN                   the account token (required)
//   PARALLAX_IMAGES                  a directory of image files, read in ordinal name order (required)
//   PARALLAX_FRAME_INTERVAL_MS       the constant interval, in milliseconds, between two frames' source time offsets (required)
//   PARALLAX_MAX_REQUEST_BYTES       the operator's per-request byte cap (required; not in the document)
//   PARALLAX_MAX_FRAMES_PER_REQUEST  the operator's per-request frame cap (required; not in the document)
//
// Run from the repository root: dotnet run --project examples/dotnet/SequenceFromImages

var directory = Required("PARALLAX_IMAGES");
var frameIntervalMs = double.Parse(Required("PARALLAX_FRAME_INTERVAL_MS"), CultureInfo.InvariantCulture);
var maxRequestBytes = long.Parse(Required("PARALLAX_MAX_REQUEST_BYTES"), CultureInfo.InvariantCulture);
var maxFramesPerRequest = int.Parse(Required("PARALLAX_MAX_FRAMES_PER_REQUEST"), CultureInfo.InvariantCulture);

var source = new DirectoryFrameSource(directory, TimeSpan.FromMilliseconds(frameIntervalMs));

var baseUrl = Environment.GetEnvironmentVariable("PARALLAX_BASE_URL");
using var client = new ParallaxClient(new ParallaxClientOptions
{
    BaseAddress = string.IsNullOrEmpty(baseUrl) ? new ParallaxClientOptions().BaseAddress : new Uri(baseUrl),
    AccountToken = Required("PARALLAX_TOKEN"),
});

var progress = new Progress<SequenceVerdictResponse>(verdict => Console.WriteLine(
    $"  verdict: state={verdict.State} framesReceived={verdict.FramesReceived} expectedSize={verdict.ExpectedSize} " +
    $"reach={verdict.Reach} connected={verdict.Connected} gaps={verdict.Gaps?.Count ?? 0} errata={verdict.Errata?.Count ?? 0}"));

var options = new SequenceRegisterOptions(TimeSpan.FromSeconds(1), 5, new SequenceBatching(maxRequestBytes, maxFramesPerRequest))
{
    Open = new SequenceOpenRequest(Array.Empty<ManifestPart>(), source.FrameCount),
};

SequenceRegisterResult result;
try
{
    result = await client.RegisterSequenceAsync(source, options, progress);
}
catch (ParallaxProblemException problem)
{
    Console.Error.WriteLine($"sequence refused: {problem.Status} {problem.Slug}: {problem.Detail}");
    return 1;
}

Console.WriteLine($"sequence hash: {result.Results.SequenceHash}");
Console.WriteLine($"outcome: {result.Results.Outcome}");
Console.WriteLine($"final size: {result.Results.FinalSize}");
foreach (var errata in result.Errata)
{
    Console.WriteLine($"  errata frame {errata.FrameId}: {errata.OriginalImageHash}");
}

var firstImage = ImageUpload.FromFile(source.FirstPath, ContentTypeFor(source.FirstPath));
var found = await client.LookupAsync(firstImage);
Console.WriteLine($"lookup matched: {found.Matched}");

return 0;

static string Required(string name)
{
    var value = Environment.GetEnvironmentVariable(name);
    if (string.IsNullOrEmpty(value))
    {
        throw new InvalidOperationException($"{name} is not set");
    }

    return value;
}

// PC-105: a minimal extension-to-media-type map for the round-trip look-up; unknown extensions fall back to a generic type
static string ContentTypeFor(string path) => Path.GetExtension(path).ToLowerInvariant() switch
{
    ".png" => "image/png",
    ".jpg" or ".jpeg" => "image/jpeg",
    ".gif" => "image/gif",
    ".webp" => "image/webp",
    ".bmp" => "image/bmp",
    _ => "application/octet-stream",
};
