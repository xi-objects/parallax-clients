// Detects the C2PA manifest store embedded in an image, shows it, attaches it explicitly on
// registration, then plays the finder: extracts the store from the file again and compares it with
// the recovered record.
//
// Environment:
//   PARALLAX_BASE_URL              the API's base URL (defaults to https://api.parallax.xiobjects.com)
//   PARALLAX_TOKEN                 the account token (required)
//   PARALLAX_IMAGE                 path of the image (required); JPEG, PNG, WebP or TIFF carriers
//   PARALLAX_IMAGE_TYPE            its media type (required)
//   PARALLAX_ATTACH_EMBEDDED_C2PA  "yes" to attach the detected store as manifest[c2pa]; anything
//                                  else registers without it (the registrant decides, never the client)
//
// Run from the repository root: dotnet run --project examples/dotnet/C2paRoundTrip

var image = ImageUpload.FromFile(Required("PARALLAX_IMAGE"), Required("PARALLAX_IMAGE_TYPE"));
var detector = new EmbeddedC2paDetector();
var detected = detector.Detect(image.Bytes);
if (detected.Carrier == C2paCarrier.Unsupported)
{
    Console.Error.WriteLine($"unsupported carrier: {detected.Detail}");
    return 1;
}

if (detected.Store is null)
{
    Console.Error.WriteLine($"{detected.Carrier}: no embedded C2PA manifest store ({detected.Detail})");
    return 1;
}

Console.WriteLine($"{detected.Carrier}: embedded C2PA store of {detected.Store.Bytes.Length} bytes:");
foreach (var box in detected.Store.Boxes)
{
    Console.WriteLine($"  {new string(' ', box.Depth * 2)}{box.Type} label={box.Label ?? "-"} length={box.Length}");
}

var manifests = new List<ManifestPart>();
if (string.Equals(Environment.GetEnvironmentVariable("PARALLAX_ATTACH_EMBEDDED_C2PA"), "yes", StringComparison.OrdinalIgnoreCase))
{
    manifests.Add(C2paAttachment.AsManifestPart(detected.Store));
    Console.WriteLine("attaching it as manifest[c2pa]");
}
else
{
    Console.WriteLine("not attaching it (set PARALLAX_ATTACH_EMBEDDED_C2PA=yes to attach)");
}

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

// The finder's side: the same detection on the file that was found, compared with the record.
var found = detector.Detect(image.Bytes);
if (found.Store is null)
{
    Console.Error.WriteLine("the found file carries no store to compare");
    return 1;
}

var comparison = new C2paRecordComparer().Compare(found.Store, record);
Console.WriteLine($"comparison: {comparison.Outcome} kind={comparison.MatchedKind ?? "-"} - {comparison.Detail}");

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
