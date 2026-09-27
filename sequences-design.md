# The sequence conversation in the .NET client (design note, 2026-09-26)

Owner brief: the client must support the sequence workflow the API now serves. HOW video is
decoded into distinct frames is set down for later; this note builds the internal service layer
and the interface that later ingestion implements. .NET only; the Python client is untouched and
no parity is required. `xio_parallax_rest`'s `sequences-initial-build.md` (rulings S1-S19) is the
design of record for the workflow; the live OpenAPI document at
`https://api.parallax.xiobjects.com/openapi/v1.json` is the contract.

## The contract (surveyed 2026-09-26, live document 1.0.0+29a207a)

- `POST /sequences` (multipart: optional `expectedSize`, `manifest[<kind>]` parts as the slot
  routes take them) -> 201 `SequenceOpenResponse { sequenceId, headFrame (the HEAD frame,
  base64), ticket }`. The account's `sequences_enabled` gate answers 403 otherwise.
- Every other route carries the header `X-Sequence-Ticket: <ticket>` (required).
- `POST /sequences/{id}/frames` (multipart: one or more file parts, any part name, each one PX
  BODY or END frame's bytes as `application/octet-stream`; the whole request bounded by the
  account's `maxRequestBytes`, 413 otherwise) -> 201 `SequenceFrameBatchResponse { frames
  [{frameId, errata}], verdict? }`; the verdict is present when the batch sealed the sequence.
  All or nothing. 409 for a state the sequence refuses, 422 when an image could not be checked,
  503 when no engine is configured.
- `DELETE /sequences/{id}/frames/{frameId}` -> 204 (open only).
- `GET /sequences/{id}/gaps` -> `SequenceGapsResponse { gaps [{from, to, gapFrame}] }`.
- `GET /sequences/{id}/progress` -> `SequenceVerdictResponse { state, framesReceived,
  expectedSize?, reach, gaps [{from, to}], errata [{frameId, originalImageHash}], connected }`.
- `PUT /sequences/{id}/expected-size` `{ expectedSize }` -> 204.
- `POST /sequences/{id}/commit` -> 200 `SequenceCommitResponse { sequenceHash?, outcome
  (registered | alreadyRegistered | incomplete), sequenceRecordPublished, frames [{frameId,
  state, originalImageHash?, refusalName?}] }`; 409 with the shortfalls when not committable;
  `incomplete` is retried by calling commit again (the server resumes from the first unpublished
  frame, S12).
- `GET /sequences/{id}/results` -> 200 `SequenceResultsResponse { sequenceHash, outcome,
  finalSize, committedAt }`; 409 before commit.
- `DELETE /sequences/{id}` -> 200 `SequenceAbandonResponse { sequenceId, state, packetsPurged }`.

The frame model (Xio.Parallax.Common 0.1.1 on nuget.org): HEAD (minted by REST, frame id 0),
BODY (client, `PxBodyHeader(sequenceId, frameId, prev, next, sourceTimeOffsetMicroseconds)` plus
buckets, the image under `PxFrameConstants.ImageBucketTag` "IMAG"), END (client,
`PxEndHeader(sequenceId, frameId, prev)`), GAP (REST only). Frame ids are longs the client owns:
monotone along the chain, every BODY's prev below its id and next above it, contiguity never
required. `IXioPxFrameEncoder.EncodeAsync(XioEncodePxFrameRequest(header, buckets))` answers the
frame bytes and the frame hash; `IXioPxFrameDecoder.DecodeAsync` reads one back (the HEAD from
open is decoded, never assumed to be id 0).

## Shape

One new domain, `Sequences/`, in `src/Xio.Parallax.Client` with `Models|Interfaces|Enums|
Services` and namespaces following folders, built exactly as `Slots/` is: generated request
builders under the hand-written layer, `ParallaxClient` partial classes, sealed records, typed
problems through the existing `ExecuteAsync` and `ParallaxProblemException`, the multipart sender
the slot upload uses, required options with no client-side default for any server cap.

1. **The generated surface.** `openapi/v1.json` is replaced by the live document and the .NET
   client regenerated with Kiota 1.35.0 (`kiota generate` line of `scripts/generate.sh`; the
   Python half of that script is NOT run and `python/` is not touched). `Xio.Parallax.Common`
   0.1.1 (nuget.org, pulling Xio.Crypto 1.0.8 from nuget.org) joins `Directory.Packages.props`
   and the client project. Package version 0.4.0.

2. **The frame source: the interface later ingestion implements.**
   `ISequenceFrameSource` — `IAsyncEnumerable<SequenceFrameInput> ReadFramesAsync(CancellationToken)`
   yielding frames in chain order. `SequenceFrameInput(long FrameId, TimeSpan SourceTimeOffset,
   IReadOnlyList<PxBucketContent> Buckets)` with a factory `ForImage(frameId, offset, imageBytes)`
   that puts the bytes under the image bucket tag. The source owns the ids (monotone, room
   allowed) and says nothing about links: the client derives prev from the previous frame it
   read (the HEAD's id for the first) and next from the following one (END's id for the last),
   buffering one frame of lookahead. A source that yields a non-monotone id is refused before
   anything is sent, naming the id.

3. **The route members** on `ParallaxClient` (`Sequences/Services/ParallaxClient.Sequences.cs`),
   one per operation, each one call: `OpenSequenceAsync(SequenceOpenRequest)` (manifests as
   `ManifestPart`s through the existing multipart builder, optional expected size) returning
   `OpenedSequence(SequenceId, Ticket, HeadFrameId)` with the HEAD decoded through Common;
   `UploadSequenceFramesAsync(SequenceHandle, IReadOnlyList<EncodedFrame>)`;
   `RemoveSequenceFrameAsync`; `GetSequenceGapsAsync`; `GetSequenceProgressAsync`;
   `AmendSequenceExpectedSizeAsync`; `CommitSequenceAsync`; `GetSequenceResultsAsync`;
   `AbandonSequenceAsync`. `SequenceHandle(SequenceId, Ticket)` carries the ticket; the header is
   set once, in one place, for every call. The ticket never reaches a log or an exception.

4. **The conversation, one call**: `RegisterSequenceAsync(ISequenceFrameSource source,
   SequenceRegisterOptions options, IProgress<SequenceVerdictResponse>? progress, ct)`:
   open (or resume through `options.Existing`), read the source, encode each BODY through Common
   with its links, upload in batches under `options.Batching` (`MaxRequestBytes`,
   `MaxFramesPerRequest`, both required), collect errata as what they are, encode END (id = the
   last BODY id + 1, prev = the last BODY id) and upload it as the sealing batch, read the
   verdict: not connected or any gap refuses with the verdict (typed
   `SequenceNotCommittableException` carrying it) and nothing is committed; then commit, repeating
   while the outcome is `incomplete` up to `options.CommitAttempts` with `options.PollInterval`
   between attempts, then results. Returns `SequenceRegisterResult(SequenceId, Ticket, Verdict,
   Commit, Results, Errata)`. Resume: `options.Existing` (sequence id and ticket) reads progress
   and gaps first; when the state is open the source is read again and only frames whose id lies
   in a gap or above the reach are uploaded, then END; when sealed, only the gaps' fills; when
   committed, commit is called again (it resumes) and results read. An account with the feature
   off, a refused batch or a shortfall surface as the typed problem the server answered.

5. **Example** `examples/dotnet/SequenceFromImages`: a directory of image files, in name order,
   as the frame source (one image per frame, ids 1..n, the source time offset from a constant
   frame interval the example states), registered through the conversation, then the results and
   one look-up of a frame proving the round trip. It is the stand-in for the ingestion that comes
   later and the proof the interface is enough.

6. **Docs**: README gains a "Sequences" section (the interface, the conversation, resume, the
   flag), CLAUDE.md's layout line names the `Sequences/` domain and the nuget.org Common
   reference, `clients-initial-build.md` gains this note under `## sequences (2026-09-26)` with
   the rulings: .NET only for now, Python untouched, Common from nuget.org, ingestion deferred.

## Rules that bind every story

- Generated code is never edited; nothing in `python/` moves.
- No client-side default for a server cap: request bytes, frames per request, poll interval,
  commit attempts are required options; a missing one throws `ArgumentException` naming it.
- Tickets and account tokens never reach a log, an exception message or a record's ToString.
- Tests with the code: xunit, the existing `FakeHttpMessageHandler` scripting responses shaped
  from the live document, a fake `ISequenceFrameSource`; encoding through the real Common
  encoder; every acceptance criterion has a backing test; no test reads markdown.
- Standards: `references/project_dev_standards.md` (the pod kit): sealed records, internal by
  default, braces on every conditional, file-scoped namespaces, every using in `GlobalUsings.cs`,
  files under 300 lines, an XML summary on every public member, one declaration per fact.
- The gate for every story: `dotnet build Xio.Parallax.Client.slnx -c Release`,
  `dotnet format Xio.Parallax.Client.slnx --verify-no-changes`,
  `dotnet test Xio.Parallax.Client.slnx -c Release --no-build`. Nothing Python runs.
- Every change site carries its story key (PC-101 .. PC-106) in one line saying what.
- No AI or assistant attribution anywhere in this repository: no co-author trailer, no session
  line, no generated-by remark, in commit messages, code comments, docs or examples.
