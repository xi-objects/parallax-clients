// Registers a whole folder of images through one slot conversation, then looks them all up in one
// look-up slot conversation. Re-running the same command after an interruption resumes: the client
// re-declares every hash and uploads only what the slot does not already hold.
//
// Environment:
//   PARALLAX_TOKEN              the account token (required)
//   PARALLAX_IMAGES             a folder of images (required)
//   PARALLAX_IMAGE_TYPE         their media type, for example image/jpeg (required)
//   PARALLAX_MAX_REQUEST_BYTES  the operator's per-request byte cap (required; not in the document)
//   PARALLAX_MAX_IMAGES         the operator's per-request image cap (required)
//   PARALLAX_SLOT_ID            optional: an open slot to resume into instead of opening a new one
//
// Run from the repository root: dotnet run --project examples/dotnet/RegisterBatch

var contentType = Required("PARALLAX_IMAGE_TYPE");
var folder = Required("PARALLAX_IMAGES");
var images = Directory.EnumerateFiles(folder)
    .OrderBy(path => path, StringComparer.Ordinal)
    .Select(path => ImageUpload.FromFile(path, contentType))
    .ToList();
if (images.Count == 0)
{
    throw new InvalidOperationException($"no files under {folder}");
}

using var client = new ParallaxClient(new ParallaxClientOptions
{
    AccountToken = Required("PARALLAX_TOKEN"),
    Batching = new UploadBatching(long.Parse(Required("PARALLAX_MAX_REQUEST_BYTES")),
                                  int.Parse(Required("PARALLAX_MAX_IMAGES"))),
});

var progress = new Progress<SlotProgressResponse>(p =>
    Console.WriteLine($"  progress: registered={p.Counts?.Registered} failed={p.Counts?.Failed} retry={p.Counts?.Retry}"));

var slotId = Environment.GetEnvironmentVariable("PARALLAX_SLOT_ID");
var registered = await client.RegisterBatchAsync(
    images.Select(image => new RegistrationItem(image, [])).ToList(),
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

static string Required(string name)
{
    var value = Environment.GetEnvironmentVariable(name);
    if (string.IsNullOrEmpty(value))
    {
        throw new InvalidOperationException($"{name} is not set");
    }

    return value;
}
