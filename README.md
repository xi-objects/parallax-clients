# XI Parallax REST clients

Client SDKs for the XI Parallax REST API (`https://api.parallax.xiobjects.com`), in .NET
(`Xio.Parallax.Client`, .NET 10) and Python (`xio-parallax-client`, Python 3.11+).

## Installing

The clients are consumed from source, never from a registry: clone or submodule this repository.

- .NET: reference `src/Xio.Parallax.Client/Xio.Parallax.Client.csproj` from your solution.
  `Xio.Parallax.Client` depends on `Xio.Parallax.Common`, which resolves from nuget.org.
- Python: `uv add --editable <path>` or `pip install <path>`, pointed at this repository's root.

## Getting started

```csharp
using var client = new ParallaxClient(new ParallaxClientOptions { AccountToken = token });

var registered = await client.RegisterAsync(ImageUpload.FromFile("photo.png", "image/png"),
                                            [new ManifestPart("c2pa", ManifestForm.C2pa, c2paBytes)]);
var found = await client.LookupAsync(ImageUpload.FromFile("photo.png", "image/png"));
```

```python
client = ParallaxClient(ParallaxClientOptions(account_token=token))

registered = client.register(ImageUpload.from_file("photo.png", "image/png"),
                             [ManifestPart("c2pa", ManifestForm.C2PA, c2pa_bytes)])
found = client.lookup(ImageUpload.from_file("photo.png", "image/png"))
```

`AsyncParallaxClient` mirrors every Python call for asyncio. Every API refusal surfaces as
`ParallaxProblemException` (.NET) / `ParallaxProblem` (Python), carrying the problem's status,
slug, detail, extensions and `Retry-After`. The .NET client's generated layer is reachable as
`client.Api` for everything the API document declares beyond what this README covers.

## Capabilities

### Registration and look-up

`RegisterAsync` / `register` and `LookupAsync` / `lookup` each run their slot conversation (open,
upload with resume, commit) as one call. Registration then polls progress to a terminal state; a
look-up commit is terminal and answers the results directly, so look-up never polls.
`RegisterBatchAsync` / `register_batch` runs the whole conversation over a folder of images in
one call, batched under a required `UploadBatching` (`MaxRequestBytes` / `max_request_bytes`,
`MaxImagesPerRequest` / `max_images_per_request`); re-running it after an interruption resumes,
since the client re-declares every hash and uploads only what the slot does not already hold.
`WaitForRecordAsync` / `wait_for_record` polls until a just-registered record is published, keyed
by `OriginalImageHash` / `original_image_hash`, the engine's own hash (not the REST `ImageHash`).
`UnregisterAsync` / `unregister` takes a record down.

### Sequences

A sequence is a video registered frame by frame rather than as one upload: the API assembles BODY
frames into a chain, seals it with an END frame, and commits it to one sequence hash the same way
a batch commits to a slot.

`ISequenceFrameSource` (.NET) / `SequenceFrameSource` and `AsyncSequenceFrameSource` (Python,
`xio_parallax_client.frames`) is the interface an ingestion that decodes a video into frames
implements, yielding frames in chain order. The source owns each frame's id (monotone, gaps
allowed) and its position within its own media (`SourceTimeOffset` / `source_time_offset`); the
client derives every frame's `prev`/`next` links from read order. `SequenceFrameInput.ForImage` /
`SequenceFrameInput.for_image` builds a frame carrying a single image bucket. A source that yields
an id not above the one before it is refused, naming the id, before that frame is sent.

`RegisterSequenceAsync(source, options, progress)` / `register_sequence(source, options,
on_verdict)` is the whole conversation in one call: open a sequence (or resume the one named by
`options.Existing` / `options.existing`), read `source`, encode and upload its frames in batches
under `options.Batching` / `options.batching` (`MaxRequestBytes` / `max_request_bytes` and
`MaxFramesPerRequest` / `max_frames_per_request`, both required), seal the sequence with an END
frame, commit it (retrying an incomplete commit up to `options.CommitAttempts` /
`options.commit_attempts`, waiting `options.PollInterval` / `options.poll_interval` between
attempts) and read its results. `progress` / `on_verdict`, when given, is called with every
verdict read along the way. A sealed verdict that is not connected, still has gaps or names errata
frames throws `SequenceVerdictException` / raises `SequenceVerdictError` carrying the verdict, and
nothing is committed.

Resume after an interruption by calling the same method again with `options.Existing` /
`options.existing` set to the `OpenedSequence` a prior run (or `OpenSequenceAsync` /
`open_sequence`) answered, rather than `options.Open` / `options.open`.

An account needs its `sequences_enabled` flag set; without it, opening a sequence is refused with
a typed problem — `ParallaxProblemException` in .NET, and in Python
`xio_parallax_client.problems.SequencesNotEnabled` (a `ParallaxProblem` subclass, matched by the
problem's slug so `except ParallaxProblem` still catches it).

### The verifier

`AttributionVerifier.Verify` / `AttributionVerifier(...).verify` recomputes the hashes of a
recovered record, checks the per-manifest, collection and image signatures, and chains the
signing certificate to trust roots you supply, returning one outcome per check, never a bare
boolean: `originalImageHash`, `contentHash` (BLAKE3-256 over the original bytes, when you have
them), `manifestHash:<kind>`, `manifestSignature:<kind>`, `collectionSignature`,
`imageSignature`, `leafKeyMatchesPublicKey`, `certificateChain`. A JSON-form manifest's hash is
reported as not recomputable, never as passed; an unknown hash algorithm, canonical version or an
empty root list is a refusal, never a skipped check. `canonicalVersion` 0 is admitted alongside 2,
for records registered through the older Forensics Lab path: that record's manifest and
collection-signature checks report not-recomputable or not-performed, never passed, while the
image signature, leaf key and certificate chain checks are unaffected. Trust roots come from
Orbital's anonymous `GET /info` (`pinnedRoots`), fetched once over TLS and pinned, or from a PEM
file.

### Embedded JUMBF and C2PA

The client, never the API, looks inside a file. `detect_embedded_c2pa` / `EmbeddedC2paDetector`
recognises a file's carrier by its signature and extracts every embedded JUMBF manifest store — a
JPEG's APP11 segments can carry several box instances, in document order; PNG (`caBX`), WebP
(`C2PA` chunk) and classic TIFF (tag 0xCD41) carry at most one — and classifies each: the C2PA
manifest-store UUID and the label `c2pa` make it kind `c2pa` (sent as `application/c2pa`), every
other well-formed store is kind `jumbf` (sent as `application/jumbf`). The result's outcome is
`FOUND`, `ABSENT`, `MALFORMED` or `UNSUPPORTED`.

Inclusion is your selection, per image: a `ManifestSelection` says whether to include the embedded
store(s) and lists the sidecars beside it, each a JSON manifest under its own kind or a JUMBF
manifest classified from its own bytes. `ManifestResolver` / `resolve_manifests` resolves every
image of a collection before anything is sent, returning one registration item per image or
refusing them all: when an image carries an embedded store and a JUMBF sidecar is offered, the two
must be byte-identical, as sets, or the resolver refuses; a malformed store, an unrecognised
carrier whenever it matters, or two manifests of one kind refuse too, naming every offending image.

`compare_with_record` / `C2paRecordComparer` compares each detected store with a recovered record
by BLAKE3 of the bytes, one outcome per store: `MATCH`, `MISMATCH`, `ABSENT_FROM_RECORD` or
`NOT_PUBLISHED`. Nothing decodes the claims or validates a C2PA signature; both the API and the
client treat a manifest as opaque bytes.

## Configuration

- `AccountToken` / `account_token` — the account token that authenticates every call (required).
- `Batching` / `batching` (`UploadBatching`) — the server's per-request byte and image caps for a
  batch registration (required; the server does not offer a default, so a batch call refuses
  without it).
- `SequenceBatching` — the server's per-request byte and frame caps for a sequence registration
  (required, same reason).
- `RecordWaitOptions` / poll options on batch and sequence calls — poll interval and poll timeout
  (required on every call that polls).
- Trust roots for the verifier — Orbital's base URL (its anonymous `GET /info`) or a PEM file
  (one of the two is required).

None of these carry a client-side default: an operator's cap, interval or timeout that the server
would otherwise refuse is a required option, never guessed.

## Examples

`examples/dotnet/GettingStarted` and `examples/python/getting_started.py` register one image,
find it, recover and verify the record, then take it down. `examples/dotnet/RegisterBatch` and
`examples/python/register_batch.py` register a folder through one slot conversation, each image's
manifests resolved from its `<image>.json`, `<image>.c2pa` and `<image>.jumbf` sidecars and, on
request, its embedded store(s), then look it up. `examples/dotnet/C2paRoundTrip` and
`examples/python/c2pa_round_trip.py` detect an image's embedded store(s), include them on request,
and compare the found file with the recovered record. `examples/dotnet/SequenceFromImages` and
`examples/python/sequence_from_images.py` register a directory of image files as one sequence,
one frame per file, then look the first one up. Each example reads its inputs from environment
variables named in its own header; `.env.example` lists every variable used across the examples —
copy it to a git-ignored `.env` and fill in your values.

## Tests

```
dotnet build Xio.Parallax.Client.slnx -c Release
dotnet test Xio.Parallax.Client.slnx -c Release --no-build
uv sync --frozen && uv run pytest
```

## License

MIT.
