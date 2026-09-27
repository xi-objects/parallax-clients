# XI Parallax REST clients

Client SDKs for the XI Parallax REST API (`https://api.parallax.xiobjects.com`), in .NET
(`Xio.Parallax.Client`, .NET 10) and Python (`xio-parallax-client`, Python 3.11+). Each wraps
registration, look-up, published records, attribution verification, embedded C2PA/JUMBF detection
and video sequences behind typed calls and typed refusals.

For the full call catalogue, options and exception types, see
[`src/Xio.Parallax.Client/README.md`](src/Xio.Parallax.Client/README.md) (.NET) and
[`python/README.md`](python/README.md) (Python).

## Installing

The clients are consumed from source, never from a registry: clone or submodule this repository.

- .NET: reference `src/Xio.Parallax.Client/Xio.Parallax.Client.csproj` from your solution.
- Python: `uv add --editable <path>` or `pip install -e <path>`, pointed at this repository's root.

## Your first registration

```csharp
using var client = new ParallaxClient(new ParallaxClientOptions { AccountToken = token });
var image = ImageUpload.FromFile("photo.png", "image/png");
var registered = await client.RegisterAsync(image, [new ManifestPart("xi-manifest", ManifestForm.Json, manifestBytes)]);
```

```python
client = ParallaxClient(ParallaxClientOptions(account_token=token))
image = ImageUpload.from_file("photo.png", "image/png")
registered = client.register(image, [ManifestPart("xi-manifest", ManifestForm.JSON, manifest_bytes)])
```

`AsyncParallaxClient` mirrors every Python call for asyncio. Manifests are optional; an image can
register with none.

## Your first look-up

```csharp
var found = await client.LookupAsync(image);
Console.WriteLine(found.Matched);
```

```python
found = client.lookup(image)
print(found.matched)
```

## Verifying a record

Once registered, a record publishes some seconds later; poll for it, then verify it against
pinned trust roots (from Orbital's anonymous `GET /info`, or a PEM file):

```csharp
var record = await client.WaitForRecordAsync(registered.OriginalImageHash!,
    new RecordWaitOptions(TimeSpan.FromSeconds(2), TimeSpan.FromMinutes(2)));
var roots = await new OrbitalTrustRootSource(httpClient).FetchAsync(orbitalUrl, cancellationToken);
var report = new AttributionVerifier().Verify(new XioVerifyRecordRequest(record, image.Bytes, roots));
Console.WriteLine(report.AllPerformedPassed);
```

```python
record = client.wait_for_record(registered.original_image_hash, RecordWaitOptions(poll_interval=2.0, poll_timeout=120.0))
roots = TrustRoots.from_orbital(orbital_url)
report = AttributionVerifier(roots).verify(record, original_image_bytes=image.data)
print(report.all_performed_passed)
```

`report` carries one verdict per check (`passed`, `failed`, `not_recomputable` or `not_performed`),
never a bare boolean; a JSON-form manifest's hash is always `not_recomputable`.

## Registering a sequence

A sequence registers a video frame by frame rather than as one upload. It needs the calling
account's `sequences_enabled` flag set; without it, opening a sequence is refused with a typed
403 (`ParallaxProblemException` in .NET; `xio_parallax_client.problems.SequencesNotEnabled`, a
`ParallaxProblem` subclass matched by slug, in Python):

```csharp
var source = new MyFrameSource(); // implements ISequenceFrameSource
var options = new SequenceRegisterOptions(TimeSpan.FromSeconds(1), commitAttempts: 5,
    new SequenceBatching(maxRequestBytes, maxFramesPerRequest)) { Open = new SequenceOpenRequest([], null) };
try
{
    var result = await client.RegisterSequenceAsync(source, options, progress);
}
catch (ParallaxProblemException problem) when (problem.Slug == "sequences-not-enabled")
{
    // the account has no sequences access
}
```

```python
try:
    result = client.register_sequence(source, options, on_verdict)
except SequencesNotEnabled:
    ...  # the account has no sequences access
```

A run that is interrupted resumes by calling the same method again with `options.Existing` /
`options.existing` set to the `OpenedSequence` a prior run answered. See the client READMEs for
the frame source contract, batching and the resulting refusal/exception types.

## Examples and their inputs

`examples/dotnet/{GettingStarted,RegisterBatch,C2paRoundTrip,SequenceFromImages}` and
`examples/python/{getting_started,register_batch,c2pa_round_trip,sequence_from_images}.py` walk
registration and look-up, a folder registered through one slot conversation, an embedded-C2PA
detect/attach/compare round trip, and a directory of images registered as one sequence.

Each example reads its inputs from environment variables named in its own header; `.env.example`
lists every variable used across the examples — copy it to a git-ignored `.env` and fill in your
values, then (bash) `set -a; . ./.env; set +a`, or (PowerShell) load it line by line. Run an
example with `dotnet run --project examples/dotnet/<Name>` or
`uv run python examples/python/<name>.py`.

## Tests

```
dotnet build Xio.Parallax.Client.slnx -c Release
dotnet test Xio.Parallax.Client.slnx -c Release --no-build
uv sync --frozen && uv run pytest
```

## License

MIT.
