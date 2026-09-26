// Detects every JUMBF manifest store embedded in an image, shows each with its classified kind (c2pa
// or jumbf), includes them explicitly on registration when asked, then plays the finder: detects the
// stores in the file again and compares each with the recovered record.
//
// Environment:
//   PARALLAX_BASE_URL          the API's base URL (defaults to https://api.parallax.xiobjects.com)
//   PARALLAX_TOKEN             the account token (required)
//   PARALLAX_IMAGE             path of the image (required); JPEG, PNG, WebP or TIFF carriers
//   PARALLAX_IMAGE_TYPE        its media type (required)
//   PARALLAX_INCLUDE_EMBEDDED  "yes" to include the embedded store(s), each as manifest[<kind>];
//                              anything else registers without them (the registrant decides, never the client)
//
// Run from the repository root: dotnet run --project examples/dotnet/C2paRoundTrip

var image = ImageUpload.FromFile(Required("PARALLAX_IMAGE"), Required("PARALLAX_IMAGE_TYPE"));
var detector = new EmbeddedC2paDetector();
var detected = detector.Detect(image.Bytes);
if (detected.Outcome != EmbeddedC2paOutcome.Found)
{
    Console.Error.WriteLine($"{detected.Carrier}: {detected.Outcome} ({detected.Detail})");
    return 1;
}

foreach (var store in detected.Stores)
{
    Console.WriteLine($"{detected.Carrier}: embedded {store.Kind} store of {store.Bytes.Length} bytes:");
    foreach (var box in store.Boxes)
    {
        Console.WriteLine($"  {new string(' ', box.Depth * 2)}{box.Type} label={box.Label ?? "-"} length={box.Length}");
    }
}

var includeEmbedded = string.Equals(Environment.GetEnvironmentVariable("PARALLAX_INCLUDE_EMBEDDED"), "yes", StringComparison.OrdinalIgnoreCase);
var manifests = new ManifestResolver().Resolve(image, new ManifestSelection(includeEmbedded, []));
Console.WriteLine(includeEmbedded
    ? $"including {string.Join(", ", manifests.Select(manifest => $"manifest[{manifest.Kind}]"))}"
    : "not including them (set PARALLAX_INCLUDE_EMBEDDED=yes to include)");

var baseUrl = Environment.GetEnvironmentVariable("PARALLAX_BASE_URL");
using var client = new ParallaxClient(new ParallaxClientOptions
{
    BaseAddress = string.IsNullOrEmpty(baseUrl) ? new ParallaxClientOptions().BaseAddress : new Uri(baseUrl),
    AccountToken = Required("PARALLAX_TOKEN"),
});
var registered = await client.RegisterAsync(image, manifests);
Console.WriteLine($"registered: {registered.Id} original image hash: {registered.OriginalImageHash}");

var record = await client.WaitForRecordAsync(
    registered.OriginalImageHash!,
    new RecordWaitOptions(TimeSpan.FromSeconds(2), TimeSpan.FromMinutes(2)));
Console.WriteLine($"record outcome: {record.Outcome}");

// The finder's side: the same detection on the file that was found, each store compared with the record.
var found = detector.Detect(image.Bytes);
if (found.Outcome != EmbeddedC2paOutcome.Found)
{
    Console.Error.WriteLine($"the found file carries no store to compare ({found.Outcome}: {found.Detail})");
    return 1;
}

var comparer = new C2paRecordComparer();
foreach (var store in found.Stores)
{
    var comparison = comparer.Compare(store, record);
    Console.WriteLine($"comparison of the {store.Kind} store: {comparison.Outcome} kind={comparison.MatchedKind ?? "-"} - {comparison.Detail}");
}

await client.UnregisterAsync(registered.Id!.Value);
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
