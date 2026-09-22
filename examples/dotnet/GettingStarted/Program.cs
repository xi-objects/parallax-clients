// The API docs' getting-started walk, with the client: token check, health, register, find,
// recover the record, verify it, take it down.
//
// Environment:
//   PARALLAX_BASE_URL       the API's base URL (defaults to https://api.parallax.xiobjects.com)
//   PARALLAX_TOKEN          the account token that registers (required)
//   PARALLAX_LOOKUP_TOKEN   a second account's token that looks the image up (defaults to PARALLAX_TOKEN)
//   PARALLAX_IMAGE          path of the image to register (required)
//   PARALLAX_IMAGE_TYPE     its media type, for example image/png (required)
//   PARALLAX_MANIFEST       optional path of a JSON manifest to attach under the kind xi-manifest
//   PARALLAX_ORBITAL_URL    Orbital's base URL, whose anonymous /info serves the pinned roots
//   PARALLAX_ROOTS_PEM      or a PEM file holding the pinned roots (one of the two is required)
//
// Run from the repository root: dotnet run --project examples/dotnet/GettingStarted

var token = Required("PARALLAX_TOKEN");
var image = ImageUpload.FromFile(Required("PARALLAX_IMAGE"), Required("PARALLAX_IMAGE_TYPE"));
var manifests = new List<ManifestPart>();
var manifestPath = Environment.GetEnvironmentVariable("PARALLAX_MANIFEST");
if (!string.IsNullOrEmpty(manifestPath))
{
    manifests.Add(new ManifestPart("xi-manifest", ManifestForm.Json, File.ReadAllBytes(manifestPath)));
}

var lookupToken = Environment.GetEnvironmentVariable("PARALLAX_LOOKUP_TOKEN");
var baseUrl = Environment.GetEnvironmentVariable("PARALLAX_BASE_URL");
var baseAddress = string.IsNullOrEmpty(baseUrl) ? new ParallaxClientOptions().BaseAddress : new Uri(baseUrl);
using var registrant = new ParallaxClient(new ParallaxClientOptions { BaseAddress = baseAddress, AccountToken = token });
using var finder = new ParallaxClient(new ParallaxClientOptions
{
    BaseAddress = baseAddress,
    AccountToken = string.IsNullOrEmpty(lookupToken) ? token : lookupToken,
});

var stats = await registrant.GetAccountStatsAsync();
Console.WriteLine($"token ok; stats: {await KiotaJsonSerializer.SerializeAsStringAsync(stats)}");
var health = await registrant.GetHealthAsync();
Console.WriteLine($"health: {await KiotaJsonSerializer.SerializeAsStringAsync(health)}");

RegisterSingleResponse registered;
try
{
    registered = await registrant.RegisterAsync(image, manifests);
}
catch (ParallaxProblemException problem)
{
    Console.Error.WriteLine($"register refused: {problem.Status} {problem.Slug}: {problem.Detail}");
    return 1;
}

Console.WriteLine(
    $"registered: {registered.Id} image hash: {registered.ImageHash} original image hash: {registered.OriginalImageHash}");

var found = await finder.LookupAsync(image);
Console.WriteLine($"lookup matched: {found.Matched} hashes: {string.Join(", ", found.MatchedOriginalImageHashes ?? [])}");

// Publication follows registration by some seconds; wait it out rather than a single look-up.
// The record store is keyed by the engine's own hash, OriginalImageHash, not REST's ImageHash.
var record = await finder.WaitForRecordAsync(
    registered.OriginalImageHash!,
    new RecordWaitOptions(TimeSpan.FromSeconds(2), TimeSpan.FromMinutes(2)));
Console.WriteLine($"record outcome: {record.Outcome}");

var report = new AttributionVerifier().Verify(new XioVerifyRecordRequest(record, image.Bytes, await TrustRootsAsync()));
foreach (var check in report.Checks)
{
    Console.WriteLine($"  {check.Name}: {check.Outcome} {check.Detail}");
}

Console.WriteLine($"all performed checks passed: {report.AllPerformedPassed}");

await registrant.UnregisterAsync(registered.Id!.Value);
Console.WriteLine($"taken down: {registered.Id}");
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

// The pinned roots, from Orbital's /info or from a PEM file; never a default.
static async Task<TrustRoots> TrustRootsAsync()
{
    var orbital = Environment.GetEnvironmentVariable("PARALLAX_ORBITAL_URL");
    if (!string.IsNullOrEmpty(orbital))
    {
        using var http = new HttpClient();
        return await new OrbitalTrustRootSource(http).FetchAsync(new Uri(orbital), CancellationToken.None);
    }

    var pem = Environment.GetEnvironmentVariable("PARALLAX_ROOTS_PEM");
    if (!string.IsNullOrEmpty(pem))
    {
        return new TrustRootReader().FromPemFile(pem);
    }

    throw new InvalidOperationException("set PARALLAX_ORBITAL_URL or PARALLAX_ROOTS_PEM");
}
