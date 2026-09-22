// Registers a whole folder of images through one slot conversation, then looks them all up in one
// look-up slot conversation. Re-running the same command after an interruption resumes: the client
// re-declares every hash and uploads only what the slot does not already hold.
//
// Environment:
//   PARALLAX_BASE_URL           the API's base URL (defaults to https://api.parallax.xiobjects.com)
//   PARALLAX_TOKEN              the account token (required)
//   PARALLAX_IMAGES             a folder of images (required)
//   PARALLAX_IMAGE_TYPE         their media type, for example image/jpeg (required)
//   PARALLAX_MAX_REQUEST_BYTES  the operator's per-request byte cap (required; not in the document)
//   PARALLAX_MAX_IMAGES         the operator's per-request image cap (required)
//   PARALLAX_SLOT_ID            optional: an open slot to resume into instead of opening a new one
//   PARALLAX_ATTACH_EMBEDDED_C2PA  "yes" to attach each image's embedded C2PA store as manifest[c2pa]
//
// Each image's manifests are what you choose to attach: a sidecar <image>.json beside the file is
// attached as manifest[xi-manifest], and the embedded C2PA store is attached only when asked.
//
// Run from the repository root: dotnet run --project examples/dotnet/RegisterBatch

var contentType = Required("PARALLAX_IMAGE_TYPE");
var folder = Required("PARALLAX_IMAGES");
var attachEmbedded = string.Equals(Environment.GetEnvironmentVariable("PARALLAX_ATTACH_EMBEDDED_C2PA"), "yes", StringComparison.OrdinalIgnoreCase);
var detector = new EmbeddedC2paDetector();
var paths = Directory.EnumerateFiles(folder)
    .Where(path => !path.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
    .OrderBy(path => path, StringComparer.Ordinal)
    .ToList();
var images = paths.Select(path => ImageUpload.FromFile(path, contentType)).ToList();
if (images.Count == 0)
{
    throw new InvalidOperationException($"no images under {folder}");
}

var items = paths.Zip(images, (path, image) => new RegistrationItem(image, ManifestsFor(path, image))).ToList();
foreach (var (path, item) in paths.Zip(items))
{
    Console.WriteLine($"  {Path.GetFileName(path)}: {(item.Manifests.Count == 0 ? "no manifests" : string.Join(", ", item.Manifests.Select(m => m.Kind)))}");
}

var baseUrl = Environment.GetEnvironmentVariable("PARALLAX_BASE_URL");
using var client = new ParallaxClient(new ParallaxClientOptions
{
    BaseAddress = string.IsNullOrEmpty(baseUrl) ? new ParallaxClientOptions().BaseAddress : new Uri(baseUrl),
    AccountToken = Required("PARALLAX_TOKEN"),
    Batching = new UploadBatching(long.Parse(Required("PARALLAX_MAX_REQUEST_BYTES")),
                                  int.Parse(Required("PARALLAX_MAX_IMAGES"))),
});

var progress = new Progress<SlotProgressResponse>(p =>
    Console.WriteLine($"  progress: registered={p.Counts?.Registered} failed={p.Counts?.Failed} retry={p.Counts?.Retry}"));

var slotId = Environment.GetEnvironmentVariable("PARALLAX_SLOT_ID");
var registered = await client.RegisterBatchAsync(
    items,
    new RegisterBatchOptions(TimeSpan.FromSeconds(1), TimeSpan.FromMinutes(5))
    {
        ExistingSlotId = string.IsNullOrEmpty(slotId) ? null : slotId,
    },
    progress);
Console.WriteLine($"slot {registered.SlotId} committed; {registered.UploadOutcomes.Count} uploads this run");
foreach (var entry in registered.FinalProgress.Entries ?? [])
{
    Console.WriteLine($"  {entry.ImageHash}: {entry.State} {entry.RegistrationId?.ToString() ?? entry.FailureReason}");
}

var found = await client.LookupBatchAsync(images, new LookupBatchOptions(TimeSpan.FromSeconds(1), TimeSpan.FromMinutes(5)), progress);
Console.WriteLine($"lookup slot {found.LookupSlotId}");
foreach (var query in found.Results.Queries ?? [])
{
    Console.WriteLine($"  {query.ImageHash}: {query.State} matched={query.Result?.Matched}");
}

// The manifests the registrant attaches for one image: its sidecar JSON, and its embedded C2PA store on request.
IReadOnlyList<ManifestPart> ManifestsFor(string path, ImageUpload image)
{
    var parts = new List<ManifestPart>();
    var sidecar = path + ".json";
    if (File.Exists(sidecar))
    {
        parts.Add(new ManifestPart("xi-manifest", ManifestForm.Json, File.ReadAllBytes(sidecar)));
    }

    if (attachEmbedded)
    {
        var found = detector.Detect(image.Bytes);
        if (found.Store is not null)
        {
            parts.Add(C2paAttachment.AsManifestPart(found.Store));
        }
    }

    return parts;
}

static string Required(string name)
{
    var value = Environment.GetEnvironmentVariable(name);
    if (string.IsNullOrEmpty(value))
    {
        throw new InvalidOperationException($"{name} is not set");
    }

    return value;
}
