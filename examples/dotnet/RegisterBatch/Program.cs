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
//   PARALLAX_INCLUDE_EMBEDDED   "yes" to include each image's embedded JUMBF manifest store(s), each
//                               under its classified kind (c2pa or jumbf)
//
// Each image's manifests are what its user chooses: a sidecar <image>.json beside the file is a JSON
// manifest of kind xi-manifest; a sidecar <image>.c2pa or <image>.jumbf is a JUMBF manifest classified
// c2pa or jumbf by its own bytes; embedded stores are included only when asked. The whole folder is
// resolved before anything is sent: a JUMBF sidecar that differs from the image's embedded store, a
// malformed store, an unrecognised carrier when the embedded store matters, or two manifests of one
// kind refuses the whole folder, every offending image listed.
//
// Run from the repository root: dotnet run --project examples/dotnet/RegisterBatch

const string JsonSidecarExtension = ".json";
string[] jumbfSidecarExtensions = [".c2pa", ".jumbf"];
string[] sidecarExtensions = [JsonSidecarExtension, .. jumbfSidecarExtensions];
var contentType = Required("PARALLAX_IMAGE_TYPE");
var folder = Required("PARALLAX_IMAGES");
var includeEmbedded = string.Equals(Environment.GetEnvironmentVariable("PARALLAX_INCLUDE_EMBEDDED"), "yes", StringComparison.OrdinalIgnoreCase);
var paths = Directory.EnumerateFiles(folder)
    .Where(path => !sidecarExtensions.Any(extension => path.EndsWith(extension, StringComparison.OrdinalIgnoreCase)))
    .OrderBy(path => path, StringComparer.Ordinal)
    .ToList();
var images = paths.Select(path => ImageUpload.FromFile(path, contentType)).ToList();
if (images.Count == 0)
{
    throw new InvalidOperationException($"no images under {folder}");
}

var requests = paths.Zip(images, (path, image) => new ManifestRequest(image, new ManifestSelection(includeEmbedded, SidecarsFor(path)))).ToList();
IReadOnlyList<RegistrationItem> items;
try
{
    items = new ManifestResolver().Resolve(requests);
}
catch (ManifestRefusalException refused)
{
    Console.Error.WriteLine($"refused {refused.Refusals.Count} image(s); nothing was sent:");
    foreach (var refusal in refused.Refusals)
    {
        Console.Error.WriteLine($"  {refusal.FileName}: {refusal.Reason}");
    }

    return 1;
}

foreach (var item in items)
{
    Console.WriteLine($"  {item.Image.FileName}: {(item.Manifests.Count == 0 ? "no manifests" : string.Join(", ", item.Manifests.Select(m => m.Kind)))}");
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

var found = await client.LookupBatchAsync(images, new LookupBatchOptions(), progress);
Console.WriteLine($"lookup slot {found.LookupSlotId}");
foreach (var query in found.Results.Queries ?? [])
{
    Console.WriteLine($"  {query.ImageHash}: {query.State} matched={query.Result?.Matched}");
}

return 0;

// The sidecars beside one image: <image>.json as kind xi-manifest, <image>.c2pa and <image>.jumbf classified by their bytes.
IReadOnlyList<SidecarManifest> SidecarsFor(string path)
{
    var sidecars = new List<SidecarManifest>();
    if (File.Exists(path + JsonSidecarExtension))
    {
        sidecars.Add(SidecarManifest.JsonFile(path + JsonSidecarExtension, "xi-manifest"));
    }

    foreach (var extension in jumbfSidecarExtensions)
    {
        if (File.Exists(path + extension))
        {
            sidecars.Add(SidecarManifest.JumbfFile(path + extension));
        }
    }

    return sidecars;
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
