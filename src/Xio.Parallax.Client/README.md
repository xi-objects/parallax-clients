# Xio.Parallax.Client

The .NET client for the XI Parallax REST API: `ParallaxClient` wraps the generated
`ParallaxApiClient` (reachable as `client.Api` for anything this library does not cover) with
authentication, typed refusals, the multipart bodies the generator cannot express, the slot and
sequence conversations as one call each, an offline attribution verifier, and embedded JUMBF/C2PA
detection.

## Constructing the client

```csharp
using var client = new ParallaxClient(new ParallaxClientOptions
{
    AccountToken = token,          // sent as Authorization: Bearer <token>
    // AdminKey = adminKey,        // sent as X-Admin-Key, when set
    // BaseAddress = new Uri(...) // defaults to https://api.parallax.xiobjects.com
    // Batching = new UploadBatching(maxRequestBytes, maxImagesPerRequest),
}, httpClient);                    // an existing HttpClient, or omit to let the client own one
```

`ParallaxClientOptions` (`Shared/Models/SharedModels.cs`):

| Member | Required | Notes |
| --- | --- | --- |
| `BaseAddress` | no | defaults to the production endpoint |
| `AccountToken` | for any authenticated call | bearer token; redacted from `ToString()` |
| `AdminKey` | no | `X-Admin-Key`; redacted from `ToString()` |
| `Batching` | for `RegisterBatchAsync`/`LookupBatchAsync` | server byte/image caps; no default. Left null, a batch call throws `ParallaxClientException` naming it |

`client.Dispose()` disposes the request adapter, the sequence frame encoder, and an owned
`HttpClient` (never one the caller supplied).

## Single-shot calls

| Call | Sends | Returns |
| --- | --- | --- |
| `RegisterAsync(image, manifests)` | `POST /registrations` | `RegisterSingleResponse` |
| `LookupAsync(image)` | `POST /lookup` | `LookupResponse` |
| `GetRecordAsync(originalImageHash)` | `GET /records/{hash}` | `PublishedRecordResponse` |
| `GetRecordsAsync(hashes)` | `POST /records` | `PublishedRecordsResponse` |
| `WaitForRecordAsync(originalImageHash, options)` | polls `GetRecordAsync` | `PublishedRecordResponse`, once terminal |
| `UnregisterAsync(registrationId)` | `DELETE /registrations/{id}` | — |
| `GetAccountStatsAsync()` | `GET /account/stats` | `AccountStatsResponse` |
| `GetHealthAsync()` | `GET /health` (anonymous) | `HealthResponse` |

`WaitForRecordAsync` polls with bounded exponential backoff starting at
`RecordWaitOptions.PollInterval`, doubling on each non-terminal poll, until the outcome is
`Published`, `TakenDown` or `Refused`, or `RecordWaitOptions.PollTimeout` elapses (then
`ParallaxClientException`). Both fields are required; there is no default.

A 503 whose `Retry-After` header is present (the "image could not be checked yet" refusal) is
retried exactly once after that wait; nothing else is retried silently.

## Batch conversations

`RegisterBatchAsync(items, options, progress)` opens a slot (or resumes
`RegisterBatchOptions.ExistingSlotId`), declares every item's SHA-256, uploads only what the slot
is missing in batches under `ParallaxClientOptions.Batching`, commits, then polls progress (same
backoff shape as above) until no entry is left `retry`; `progress` is reported on every poll. An
image the account already registered lands `errata` in the outcomes, never a thrown exception.
Returns `RegisterBatchResult` (`SlotId`, `Commit`, `FinalProgress`, `UploadOutcomes`).

`LookupBatchAsync(images, options, progress)` is the look-up mirror: opens (or resumes
`LookupBatchOptions.ExistingLookupSlotId`), uploads only missing hashes, commits. A look-up commit
is terminal and answers results directly, so this never polls for them — it reads `/progress`
once, after commit, purely to report it. Returns `LookupBatchResult` (`LookupSlotId`, `Results`,
`FinalProgress`).

Re-running either call with the same items and the slot id a first run opened is how a caller
resumes after an interruption: only what the slot still lacks is re-uploaded.

`RegistrationItem(Image, Manifests)` is one item of a register batch.

## Sequences

A sequence is a video registered frame by frame: BODY frames chained together, sealed with an
END frame, committed to one sequence hash.

`ISequenceFrameSource.ReadFramesAsync` streams `SequenceFrameInput`s in chain order. The source
owns each frame's id (monotone; gaps allowed) and its `SourceTimeOffset` (position within its own
media); the client derives every frame's prev/next from read order — a non-monotone id is refused,
naming both ids, before it is sent. `SequenceFrameInput.ForImage(frameId, sourceTimeOffset,
imageBytes)` builds a frame carrying a single image bucket; the explicit constructor validates a
positive id, a non-negative offset, at least one well-formed, non-empty, non-repeated bucket,
naming every violation together.

`RegisterSequenceAsync(source, options, progress)` is the whole conversation in one call: open (or
resume `SequenceRegisterOptions.Existing`), read `source`, encode and upload frames in batches
under `options.Batching` (`SequenceBatching.MaxRequestBytes`/`MaxFramesPerRequest`, both required),
seal with END, commit (retrying an `incomplete` outcome up to `options.CommitAttempts`, waiting
`options.PollInterval` between attempts), and read results. `progress` is called with every
verdict read along the way. Resuming (`options.Existing` set instead of `options.Open`) sends only
what is missing: an open sequence gets frames past its reach or inside a gap, then END; a sealed
one only its gap fills; a committed one only its commit retried.

Exactly one of `SequenceRegisterOptions.Open`/`Existing` must be set (else `ArgumentException`).

The nine route members, callable individually (each takes a `SequenceHandle` — id + ticket — and
sends the ticket as `X-Sequence-Ticket`, the one route without a ticket being `OpenSequenceAsync`
itself):

| Member | Sends |
| --- | --- |
| `OpenSequenceAsync(request)` | `POST /sequences` — manifest parts, optional `expectedSize` |
| `UploadSequenceFramesAsync(handle, frames)` | `POST /sequences/{id}/frames` — one octet-stream part per frame |
| `RemoveSequenceFrameAsync(handle, frameId)` | `DELETE /sequences/{id}/frames/{frameId}` |
| `GetSequenceGapsAsync(handle)` | `GET /sequences/{id}/gaps` |
| `GetSequenceProgressAsync(handle)` | `GET /sequences/{id}/progress` |
| `AmendSequenceExpectedSizeAsync(handle, expectedSize)` | `PUT /sequences/{id}/expected-size` |
| `CommitSequenceAsync(handle)` | `POST /sequences/{id}/commit` |
| `GetSequenceResultsAsync(handle)` | `GET /sequences/{id}/results` |
| `AbandonSequenceAsync(handle)` | `DELETE /sequences/{id}` |

`OpenedSequence` (`Handle`, `HeadFrameId`) is what `OpenSequenceAsync` and a resumed
`RegisterSequenceAsync` answer. `SequenceHandle.ToString()` redacts `Ticket`.

## Refusals and exceptions

| Type | Raised when |
| --- | --- |
| `ParallaxProblemException` | Any non-2xx API response; carries `Status`, `Type`, `Slug`, `Title`, `Detail`, `TraceId`, `Cap`, `RegistrationId`, `RegistrationRemaining`, `LookupRemaining`, `RetryAfter` |
| `ParallaxClientException` | The client refuses to guess: batching without `Batching`, or a poll timing out |
| `SequenceVerdictException` | A sealed sequence's verdict is not connected, still has gaps, or names errata frames; nothing is committed, and the sequence stays sealed |
| `SequenceCommitException` | A commit is still `incomplete` after every `CommitAttempts` allowed |
| `ManifestRefusalException` | Manifest resolution (below) refused one or more images; nothing is resolved for any of them |
| `VerificationRefusedException` | The verifier cannot check a record at all (below) |

`ParallaxProblemException.Slug` is the trailing segment of the problem's
`urn:xio:parallax:problem:<slug>` type; match on it (for example `"sequences-not-enabled"`) rather
than on status alone, since more than one refusal shares a status code.

## The verifier

`new AttributionVerifier().Verify(new XioVerifyRecordRequest(record, originalImageBytes, roots))`
recomputes a published record's hashes, checks its Ed25519 signatures and chains its leaf
certificate to pinned roots, returning a `VerificationReport` of one `VerificationCheck` (`Name`,
`Outcome`, `Detail`) per check, never a bare boolean:

- `originalImageHash`, `contentHash` (needs `originalImageBytes`; `NotPerformed` without it)
- `manifestHash:<kind>`, `manifestSignature:<kind>` — one pair per manifest
- `collectionSignature`, `imageSignature`, `leafKeyMatchesPublicKey`, `certificateChain`

`VerificationOutcome` is `Passed`, `Failed`, `NotRecomputable` (a JSON-form manifest's hash: its
stored bytes are the carrier's own JUMBF, which the record does not return — never reported as
`Passed`) or `NotPerformed`. `VerificationReport.AllPerformedPassed` is true when every check that
ran passed, excluding `NotRecomputable`/`NotPerformed`.

`canonicalVersion` 0 (legacy, the older Forensics Lab path) is admitted alongside 2: its manifest
and collection-signature checks report `NotRecomputable`/`NotPerformed`, never `Passed`; the image
signature, leaf key and certificate chain checks are unaffected.

`Verify` throws `VerificationRefusedException` for: no trust roots; a record with no verification
block; a canonical version other than 0 or 2; a hash algorithm other than BLAKE3-256; a signature
algorithm other than Ed25519; or a content hash that is not a 32-byte hex digest.

Trust roots (`TrustRoots`, never empty):

- `new OrbitalTrustRootSource(httpClient).FetchAsync(orbitalBaseUrl, cancellationToken)` — GETs
  `{orbitalBaseUrl}/info` anonymously and pins its `pinnedRoots` PEM array; throws
  `VerificationRefusedException` on a non-success response, a missing `pinnedRoots`, or an empty
  list ("Control not activated").
- `new TrustRootReader().FromPem(pems)` / `.FromPemFile(path)` — pins certificates from PEM text
  or a file; throws `VerificationRefusedException` if none is found.

## Embedded JUMBF and C2PA

The client, never the API, looks inside a file.

Detection, the JUMBF walk and the manifest merge come from the
[`Xio.Parallax.Manifests`](https://www.nuget.org/packages/Xio.Parallax.Manifests) package.
`services.AddXioParallaxManifests()` registers `IEmbeddedJumbfDetector`,
`IJumbfStoreReader` and `IManifestMerger`; the package's README gives the carriers it reads (JPEG,
PNG, WebP, TIFF/DNG, GIF, HEIF/HEIC/AVIF) and how each store is classified `c2pa` (sent as
`application/c2pa`) or `jumbf` (`application/jumbf`). Any other format carries no embedded store.

`C2paAttachment.AsManifestPart(store)` turns a detected `EmbeddedJumbfStore` into a `ManifestPart` of its
classified kind and form, to attach explicitly.

`C2paRecordComparer.Compare(store, record)` compares a detected store's BLAKE3-256 against the
declared hash of each of the record's `jumbf`-form manifests (never `json`-form): `Match`
(`MatchedKind` set), `Mismatch`, `AbsentFromRecord`, or `NotPublished` (the record's outcome is not
`Published`).

**Manifest selection.** `ManifestSelection(IncludeEmbedded, Sidecars)` is what one image's user
chose: whether to include every embedded store, and which sidecars go beside it.
`SidecarManifest.Json(name, kind, bytes)` / `.JsonFile(path, kind)` is a JSON sidecar of a stated
kind; `.Jumbf(name, bytes)` / `.JumbfFile(path)` is a JUMBF sidecar whose kind is classified from
its own bytes at resolution — `ManifestForm.C2pa` is a classification result, never a valid
sidecar form, and is refused at construction.

`new ManifestResolver().Resolve(requests)` (a list of `ManifestRequest(Image, Selection)`) or
`.Resolve(image, selection)` resolves every image's parts (sidecars first in given order, then,
with `IncludeEmbedded`, the embedded stores merged in by `IManifestMerger` in document order)
before anything is sent. The merge adds every embedded JUMBF store, C2PA or not, unless its bytes
are already in the list; distinct plain `jumbf` stores may repeat. It refuses (naming every
offending image, resolving nothing) when: an image would carry more than one distinct C2PA
manifest across its sidecars and embedded stores; its embedding or a JUMBF sidecar is malformed;
or two JSON manifests share one kind. Without `IncludeEmbedded` the image's embedding is not read.
Inclusion is always the caller's own selection � the register calls send exactly what was
resolved, never a client-side default.

## Account-side inputs the integrator supplies

None of these carry a client-side default; the client refuses rather than guess:

- `ParallaxClientOptions.AccountToken` — required for any authenticated call.
- `ParallaxClientOptions.Batching` (`UploadBatching.MaxRequestBytes`/`MaxImagesPerRequest`) —
  required by `RegisterBatchAsync`/`LookupBatchAsync`; the server's per-request caps are not in
  the OpenAPI document.
- `SequenceRegisterOptions.Batching` (`SequenceBatching.MaxRequestBytes`/`MaxFramesPerRequest`) —
  same reason, for sequence frame uploads.
- `RecordWaitOptions.PollInterval`/`PollTimeout` and `RegisterBatchOptions.PollInterval`/
  `PollTimeout` — how long to wait between polls and before giving up; only the caller knows what
  is reasonable.
- `SequenceRegisterOptions.PollInterval`/`CommitAttempts` — the same, for a sequence's commit
  retries.
- Trust roots for `AttributionVerifier` — Orbital's base URL or a PEM file, one of the two.
