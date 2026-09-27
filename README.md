# XI Parallax REST clients

Client SDKs for the XI Parallax REST API (`https://api.parallax.xiobjects.com`), in .NET
(`Xio.Parallax.Client`, .NET 10) and Python (`xio-parallax-client`, Python 3.11+). Both are
generated from the API's OpenAPI document, pinned at `openapi/v1.json` and refreshed by hand from
the live document when the contract changes. On top of the generated code each package carries a hand-written layer for
the three things a generator cannot give:

- the multipart request with `manifest[<kind>]` parts, which the document can only describe;
- the slot conversations as one call each, for registration and for look-up: open, upload with
  resume, commit. Registration then polls progress to a terminal state; a look-up commit is
  terminal and answers the results directly, so look-up never polls;
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

## Sequences

A sequence is a video registered frame by frame rather than as one upload: the API assembles
BODY frames into a chain, seals it with an END frame, and commits it to one sequence hash the
same way a batch commits to a slot. This is a .NET-only conversation for now; the Python client
is untouched.

`ISequenceFrameSource` is the interface a later ingestion (something that decodes a video into
frames) implements: `IAsyncEnumerable<SequenceFrameInput> ReadFramesAsync(CancellationToken)`,
yielding frames in chain order. The source owns each frame's id (monotone, room between them is
allowed) and its position within its own media (`SourceTimeOffset`); it says nothing about the
links between frames — the client derives every frame's `prev` from the frame read immediately
before it (the sequence's HEAD id for the first) and its `next` from the frame read immediately
after it, buffering one frame of lookahead. `SequenceFrameInput.ForImage(frameId, offset,
imageBytes)` builds a frame carrying a single image bucket. A source that yields an id not above the
one before it is refused, naming the id, before that frame (or any batch holding it) is sent;
batches before it may already have been uploaded, and re-sending them on a later run is harmless.

`RegisterSequenceAsync(source, options, progress)` is the whole conversation in one call: open a
sequence (or resume the one named by `options.Existing`), read `source`, encode and upload its
frames in batches under `options.Batching` (`MaxRequestBytes`, bounding each request's whole
multipart body, and `MaxFramesPerRequest` — both required, with no client-side default for either
server cap), seal the sequence with an END frame, commit it (retrying an incomplete commit up to
`options.CommitAttempts`, waiting `options.PollInterval` between attempts) and read its results.
`progress`, when given, is reported with every verdict the conversation reads along the way. A
sealed verdict that is not connected, still has gaps or names errata frames throws
`SequenceVerdictException` carrying the verdict, and nothing is committed: the sequence stays
sealed for you to abandon or to resolve through take-down.

```csharp
var options = new SequenceRegisterOptions(TimeSpan.FromSeconds(1), CommitAttempts: 5, batching)
{
    Open = new SequenceOpenRequest(manifests, ExpectedSize: frameCount),
};
var result = await client.RegisterSequenceAsync(source, options, progress);
Console.WriteLine($"{result.Results.SequenceHash}: {result.Results.Outcome}");
```

Resume after an interruption by calling `RegisterSequenceAsync` again with
`options.Existing` set to the `OpenedSequence` a first run answered (or that `OpenSequenceAsync`
answered directly), rather than `options.Open`: an open sequence gets only the frames inside a
gap or above its reach, then the END frame; a sealed one gets only its gap fills; a committed one
just has commit called again (the server resumes from the first unpublished frame) and its
results read.

An account needs its `sequences_enabled` flag set; without it, opening a sequence is refused with
the typed problem the server answers, the same as any other refusal.

`examples/dotnet/SequenceFromImages` is the stand-in for the ingestion that decodes a video into
frames: it reads a directory of image files, in ordinal name order, as one sequence's frames
(frame ids 1..n, each frame's source time offset the constant frame interval it is given),
refusing any file whose extension is not an image's, registers them through
`RegisterSequenceAsync`, prints every verdict, the sequence hash, the outcome and the final size
(or, on a refused verdict, its errata frames), then looks its first image up through `LookupAsync`
to prove the round trip.

## The verifier

`verify` returns a report with one outcome per check, never a bare boolean: `originalImageHash`
(the record is keyed by its own content hash in hex), `contentHash` (BLAKE3-256 over the original
bytes, when you have them), `manifestHash:<kind>`, `manifestSignature:<kind>`,
`collectionSignature`, `imageSignature`, `leafKeyMatchesPublicKey`, `certificateChain`. A
JSON-form manifest's hash is reported as not recomputable, never as passed; an unknown hash
algorithm, canonical version or an empty root list is a refusal, never a skipped check.
`canonicalVersion` 0 is admitted alongside 2, for records registered through the older Forensics
Lab path: since this verifier implements no version-0 canonical preimage, that record's manifest
and collection-signature checks report not-recomputable or not-performed, never passed, while the
image signature, leaf key and certificate chain checks are unaffected. The roots
come from Orbital's anonymous `GET /info` (`pinnedRoots`), fetched once over TLS and pinned, or
from a PEM file. Both verifiers carry a conformance test over a real record captured from the
API's own e2e stack (`fixtures/record/`), and every performed check passes on it.

## Embedded JUMBF and C2PA

The client, never the API, looks inside a file. REST validates that a manifest is well-formed
JUMBF; it never requires that JUMBF be C2PA, so every well-formed store is shown, not just C2PA's
own. `detect_embedded_c2pa` / `EmbeddedC2paDetector` recognises a file's carrier by its signature
and extracts every embedded JUMBF manifest store — a JPEG's APP11 segments can carry several box
instances, in document order; PNG (`caBX`), WebP (`C2PA` chunk) and classic TIFF (tag 0xCD41)
carry at most one — and classifies each: the C2PA manifest-store UUID and the label `c2pa` make it
kind `c2pa` (sent as `application/c2pa`), every other well-formed store is kind `jumbf` (sent as
`application/jumbf`); classification never refuses. The result's outcome is `FOUND`, `ABSENT`,
`MALFORMED` or `UNSUPPORTED`: a malformed instance, or two stores of one kind, is `MALFORMED`
naming the count; a supported carrier with no store is `ABSENT`; an unrecognised carrier is
`UNSUPPORTED`, never "no C2PA".

Inclusion is your selection, per image: a `ManifestSelection` says whether to include the
embedded store(s) and lists the sidecars beside it, each a JSON manifest under its own kind or a
JUMBF manifest classified from its own bytes. `ManifestResolver` / `resolve_manifests` resolves
every image of a collection before anything is sent, returning one registration item per image or
refusing them all.

```csharp
var requests = images.Select(image => new ManifestRequest(image,
    new ManifestSelection(IncludeEmbedded: true, [SidecarManifest.Json("meta.json", "xi-manifest", jsonBytes)])))
    .ToList();
try
{
    var items = new ManifestResolver().Resolve(requests);
}
catch (ManifestRefusalException refused)
{
    foreach (var refusal in refused.Refusals)
    {
        Console.Error.WriteLine($"{refusal.FileName}: {refusal.Reason}");
    }
}
```

```python
requests = [ManifestRequest(image, ManifestSelection(include_embedded=True,
                            sidecars=[SidecarManifest.json("meta.json", "xi-manifest", json_bytes)]))
            for image in images]
try:
    items = resolve_manifests(requests)
except ManifestRefusalError as refused:
    for refusal in refused.refusals:
        print(refusal.file_name, refusal.reason)
```

The conflict rule: when an image carries an embedded store and a JUMBF sidecar is offered, the two
must be byte-identical — with several of either, the two sets must match exactly; identical bytes
are one manifest, included once, and anything else refuses. Whenever the embedded content matters
(inclusion requested, or any JUMBF sidecar given), a malformed store refuses, an unrecognised
carrier refuses since the client never skips the check, and a supported carrier with no store
simply contributes nothing. Two manifests of one kind on one image refuse, and a JSON sidecar
never conflicts with an embedded store.

On the finder's side, `compare_with_record` / `C2paRecordComparer` compares each detected store
with the recovered record by BLAKE3 of the bytes, one outcome per store: `MATCH`, `MISMATCH`,
`ABSENT_FROM_RECORD` or `NOT_PUBLISHED`. Nothing decodes the claims or validates a C2PA signature;
the API and the client both treat a manifest as opaque bytes.

## Examples

`examples/dotnet/GettingStarted` and `examples/python/getting_started.py` walk the docs'
sequence; `examples/dotnet/RegisterBatch` and `examples/python/register_batch.py` register a
folder through one slot conversation, each image's manifests resolved from its `<image>.json`
(kind `xi-manifest`), `<image>.c2pa` and `<image>.jumbf` sidecars and, on request, its embedded
store(s), then look it up through another; `examples/dotnet/C2paRoundTrip` and
`examples/python/c2pa_round_trip.py` detect the embedded store(s), include them on request, and
compare the found file with the recovered record. Each reads its inputs from environment
variables named in its header, including `PARALLAX_INCLUDE_EMBEDDED`; `.env.example` names them
all, and a git-ignored `.env` holds your values. All of them have been run against the API's own
e2e stack and against production, with the roots pinned from the live Orbital's `/info`.
`examples/dotnet/SequenceFromImages` is described above, under Sequences.

## Building

```
dotnet build Xio.Parallax.Client.slnx -c Release
dotnet format Xio.Parallax.Client.slnx --verify-no-changes
dotnet test Xio.Parallax.Client.slnx -c Release --no-build
uv sync --frozen && uv run ruff check python examples/python && uv run pytest
```

`scripts/generate.sh` regenerates both clients from `openapi/v1.json` (Kiota at the version
`kiota-lock.json` names, openapi-python-client through `uvx`). When the API's contract changes,
fetch the live document over the pin and regenerate:

```
curl -fsS -o openapi/v1.json https://api.parallax.xiobjects.com/openapi/v1.json
sh scripts/generate.sh
```

`scripts/openapi-changed.py` tells whether two documents are the same contract, ignoring the
build commit in `info.version`. There is no CI: nothing is shipped. `clients-initial-build.md`
is the design of record.

## Publishing

`Xio.Parallax.Client` is also published, by hand, as a NuGet package to the organisation's Azure
DevOps Artifacts feed. Run `.\publish.ps1 -FeedUrl <feed-url> [-Version x.y.z]` from the repo
root (`az login` or `$env:NUGET_PAT` for credentials); the version lives in
`src/Xio.Parallax.Client/Xio.Parallax.Client.csproj`.
