# XI Parallax REST clients

Client SDKs for the XI Parallax REST API (`https://api.parallax.xiobjects.com`), in .NET
(`Xio.Parallax.Client`, .NET 10) and Python (`xio-parallax-client`, Python 3.11+). Both are
generated from the API's OpenAPI document, pinned at `openapi/v1.json` and refreshed by CI from
the live document. On top of the generated code each package carries a hand-written layer for
the three things a generator cannot give:

- the multipart request with `manifest[<kind>]` parts, which the document can only describe;
- the slot conversations (open, upload with resume, commit, poll) as one call each, for
  registration and for look-up;
- the attribution verifier: it recomputes the hashes of a recovered record, checks the
  per-manifest, collection and image signatures, and chains the signing certificate to the
  pinned trust roots, so an integrator never takes the API's word for it.

The clients are consumed from source, never from a registry: clone or submodule this repository,
reference `src/Xio.Parallax.Client/Xio.Parallax.Client.csproj` from your solution, and install the
Python package from the tree (`uv add --editable <path>` or `pip install <path>`).

## .NET

```csharp
using var client = new ParallaxClient(new ParallaxClientOptions
{
    AccountToken = token,
    Batching = new UploadBatching(MaxRequestBytes: 50_000_000, MaxImagesPerRequest: 20),
});

// The docs' getting-started walk.
var registered = await client.RegisterAsync(ImageUpload.FromFile("photo.png", "image/png"),
                                            [new ManifestPart("c2pa", ManifestForm.C2pa, c2paBytes)]);
var found = await client.LookupAsync(ImageUpload.FromFile("photo.png", "image/png"));
// Publication follows registration by some seconds; wait it out rather than a single look-up.
// The record store is keyed by the engine's own hash, OriginalImageHash, not REST's ImageHash.
var record = await client.WaitForRecordAsync(
    registered.OriginalImageHash!, new RecordWaitOptions(TimeSpan.FromSeconds(2), TimeSpan.FromMinutes(2)));
await client.UnregisterAsync(registered.Id!.Value);

// A whole folder in one slot conversation; run it again after an interruption to resume.
var result = await client.RegisterBatchAsync(items, options, progress);

// Verify a recovered record against roots pinned once from Orbital.
using var http = new HttpClient();
var roots = await new OrbitalTrustRootSource(http).FetchAsync(new Uri(orbitalUrl), ct);
var report = new AttributionVerifier().Verify(new XioVerifyRecordRequest(record, originalBytes, roots));
```

Every API refusal surfaces as `ParallaxProblemException` with the problem's status, slug,
detail, extensions and `Retry-After`. The generated client is reachable as `client.Api` for
everything the document declares. The server's upload caps are operator configuration, not in
the document, so a batch call refuses without `Batching` rather than guessing.

## Python

```python
from xio_parallax_client import (ImageUpload, ManifestForm, ManifestPart, ParallaxClient,
                                 ParallaxClientOptions, RecordWaitOptions, RegisterBatchOptions,
                                 RegistrationItem, UploadBatching)
from xio_parallax_client.verification import AttributionVerifier, TrustRoots

client = ParallaxClient(ParallaxClientOptions(account_token=token,
                                              batching=UploadBatching(50_000_000, 20)))

registered = client.register(ImageUpload.from_file("photo.png", "image/png"),
                             [ManifestPart("c2pa", ManifestForm.C2PA, c2pa_bytes)])
found = client.lookup(ImageUpload.from_file("photo.png", "image/png"))
# Publication follows registration by some seconds; wait_for_record polls until it lands.
record = client.wait_for_record(registered.original_image_hash,
                                RecordWaitOptions(poll_interval=2.0, poll_timeout=120.0))
client.unregister(str(registered.id))

result = client.register_batch([RegistrationItem(image) for image in images],
                               RegisterBatchOptions(poll_interval=1.0, poll_timeout=300.0))

report = AttributionVerifier(TrustRoots.from_orbital(orbital_url)).verify(record, original_bytes)
```

`AsyncParallaxClient` mirrors every call for asyncio. Refusals raise `ParallaxProblem`.

## The verifier

`verify` returns a report with one outcome per check, never a bare boolean: `originalImageHash`
(the record is keyed by its own content hash in hex), `contentHash` (BLAKE3-256 over the original
bytes, when you have them), `manifestHash:<kind>`, `manifestSignature:<kind>`,
`collectionSignature`, `imageSignature`, `leafKeyMatchesPublicKey`, `certificateChain`. A
JSON-form manifest's hash is reported as not recomputable, never as passed; an unknown hash
algorithm, canonical version or an empty root list is a refusal, never a skipped check. The roots
come from Orbital's anonymous `GET /info` (`pinnedRoots`), fetched once over TLS and pinned, or
from a PEM file. Both verifiers carry a conformance test over a real record captured from the
API's own e2e stack (`fixtures/record/`), and every performed check passes on it.

## Examples

`examples/dotnet/GettingStarted` and `examples/python/getting_started.py` walk the docs'
sequence; `examples/dotnet/RegisterBatch` and `examples/python/register_batch.py` register a
folder through one slot conversation and look it up through another. Each reads its inputs from
environment variables named in its header.

## Building

```
dotnet build Xio.Parallax.Client.slnx -c Release
dotnet format Xio.Parallax.Client.slnx --verify-no-changes
dotnet test Xio.Parallax.Client.slnx -c Release --no-build
uv sync --frozen && uv run ruff check python examples/python && uv run pytest
```

`scripts/generate.sh` regenerates both clients from `openapi/v1.json` (Kiota at the version
`kiota-lock.json` names, openapi-python-client through `uvx`); CI fails when the committed
generated code differs from what the pin produces, and the daily `regenerate` workflow opens a
pull request when the live document changes. `clients-initial-build.md` is the design of record.
