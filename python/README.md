# xio-parallax-client

The Python client for the XI Parallax REST API: `ParallaxClient` (and its asyncio mirror
`AsyncParallaxClient`) wraps a generated `AuthenticatedClient` (`.api`) with typed refusals, the
multipart bodies the generator cannot express, the slot and sequence conversations as one call
each, an offline attribution verifier, and embedded JUMBF/C2PA detection. Everything below is
importable from `xio_parallax_client` unless another module is named.

## Constructing the client

```python
client = ParallaxClient(
    ParallaxClientOptions(
        account_token=token,       # sent as Authorization: Bearer <token>
        # admin_key=admin_key,     # sent as X-Admin-Key, when set
        # base_url="...",         # defaults to https://api.parallax.xiobjects.com
        # batching=UploadBatching(max_request_bytes, max_images_per_request),
    ),
    httpx_client,                  # an existing httpx.Client, or omit to let it build one
    frame_codec=None,              # a PxFrameCodec; see "The PX Frame codec extension point"
)
```

`AsyncParallaxClient` takes the same arguments over `httpx.AsyncClient`.

`ParallaxClientOptions` (`options.py`), a frozen dataclass:

| Field | Required | Notes |
| --- | --- | --- |
| `base_url` | no | defaults to the production endpoint |
| `account_token` | for any authenticated call | bearer token; excluded from `repr()` |
| `admin_key` | no | `X-Admin-Key`; excluded from `repr()` |
| `batching` | for `register_batch`/`lookup_batch` | `UploadBatching`; server byte/image caps, no default. Left `None`, a batch call raises `ParallaxClientError` naming it |

## Single-shot calls

| Call | Sends | Returns |
| --- | --- | --- |
| `register(image, manifests=())` | `POST /registrations` | `RegisterSingleResponse` |
| `lookup(image)` | `POST /lookup` | `LookupResponse` |
| `get_record(original_image_hash)` | `GET /records/{hash}` | `PublishedRecordResponse` |
| `get_records(hashes)` | `POST /records` | `PublishedRecordsResponse` |
| `wait_for_record(original_image_hash, options)` | polls `get_record` | `PublishedRecordResponse`, once terminal |
| `unregister(registration_id)` | `DELETE /registrations/{id}` | — |
| `account_stats()` | `GET /account/stats` | `AccountStatsResponse` |
| `health()` | `GET /health` (anonymous) | `HealthResponse` |

`wait_for_record` polls with bounded exponential backoff from `RecordWaitOptions.poll_interval`
until the outcome is `published`, `takenDown` or `refused`, or `poll_timeout` elapses (then
`ParallaxClientError`). Both fields are required; there is no default.

A 503 whose `Retry-After` header is present (the "image could not be checked yet" refusal) is
retried exactly once after that wait; every other non-2xx raises `ParallaxProblem` immediately.

## Batch conversations

`register_batch(items, options, on_progress=None)` opens a slot (or resumes
`RegisterBatchOptions.existing_slot_id`), declares every item's SHA-256, uploads only what the
slot is missing in batches under `ParallaxClientOptions.batching`, commits, then polls progress
until no entry is left `retry`; `on_progress` is called on every poll. An image the account
already registered lands `errata` in the outcomes, never a raised exception. Returns
`RegisterBatchResult` (`slot_id`, `commit`, `final_progress`, `upload_outcomes`).

`lookup_batch(images, options, on_progress=None)` is the look-up mirror: opens (or resumes
`LookupBatchOptions.existing_lookup_slot_id`), uploads only missing hashes, commits. A look-up
commit is terminal and answers results directly, so this never polls for them — it reads progress
once, after commit, purely to report it. Returns `LookupBatchResult` (`lookup_slot_id`, `results`,
`final_progress`).

Re-running either call with the same items and the slot id a first run opened is how a caller
resumes after an interruption: only what the slot still lacks is re-uploaded.

`RegistrationItem(image, manifests=())` is one item of a register batch.

## Sequences

A sequence is a video registered frame by frame: BODY frames chained together, sealed with an END
frame, committed to one sequence hash.

`SequenceFrameSource.read_frames()` (and `AsyncSequenceFrameSource.read_frames_async()`) yields
`SequenceFrameInput`s in chain order. The source owns each frame's `frame_id` (monotone; gaps
allowed) and its `source_time_offset` (position within its own media); the client derives every
frame's prev/next from read order. `SequenceFrameInput.for_image(frame_id, source_time_offset,
image_bytes)` builds a frame carrying a single image bucket; `__post_init__` validates a positive
id, a non-negative offset, at least one well-formed, non-empty, non-repeated bucket, naming every
violation together in one `ValueError`.

`register_sequence(source, options, on_verdict=None)` is the whole conversation in one call: open
(or resume `SequenceRegisterOptions.existing`), read `source`, encode and upload frames in batches
under `options.batching` (`SequenceBatching.max_request_bytes`/`max_frames_per_request`, both
required), seal with END, commit (retrying an `incomplete` outcome up to
`options.commit_attempts`, waiting `options.poll_interval` between attempts), and read results.
`on_verdict` is called with every verdict read along the way. Resuming (`options.existing` set
instead of `options.open`) sends only what is missing: an open sequence gets frames past its reach
or inside a gap, then END; a sealed one only its gap fills; a committed one only its commit
retried.

Exactly one of `SequenceRegisterOptions.open`/`existing` must be set (else `ValueError`).

The nine route members, callable individually (each takes a `SequenceHandle` — `sequence_id` +
`ticket` — and sends the ticket as `X-Sequence-Ticket`, the one route without a ticket being
`open_sequence` itself):

| Member | Sends |
| --- | --- |
| `open_sequence(request)` | `POST /sequences` — manifest parts, optional `expectedSize` |
| `upload_sequence_frames(handle, frames)` | `POST /sequences/{id}/frames` — one octet-stream part per frame |
| `remove_sequence_frame(handle, frame_id)` | `DELETE /sequences/{id}/frames/{frameId}` |
| `get_sequence_gaps(handle)` | `GET /sequences/{id}/gaps` |
| `get_sequence_progress(handle)` | `GET /sequences/{id}/progress` |
| `amend_sequence_expected_size(handle, expected_size)` | `PUT /sequences/{id}/expected-size` |
| `commit_sequence(handle)` | `POST /sequences/{id}/commit` |
| `get_sequence_results(handle)` | `GET /sequences/{id}/results` |
| `abandon_sequence(handle)` | `DELETE /sequences/{id}` |

`OpenedSequence` (`handle`, `head_frame_id`) is what `open_sequence` and a resumed
`register_sequence` answer. `SequenceHandle`'s `repr()` redacts `ticket`.

## Refusals and exceptions

| Type | Raised when |
| --- | --- |
| `ParallaxProblem` | Any non-2xx API response; carries `status`, `type`, `slug`, `title`, `detail`, `trace_id`, `cap`, `registration_id`, `registration_remaining`, `lookup_remaining`, `retry_after` |
| `SequencesNotEnabled` | A `ParallaxProblem` subclass, matched by slug `sequences-not-enabled`: the calling account has no Sequences access |
| `ParallaxClientError` | The client refuses to guess: batching without `batching`, or a poll timing out |
| `SequenceVerdictError` | A sealed sequence's verdict is not connected, still has gaps, or names errata frames; nothing is committed, and the sequence stays sealed |
| `SequenceCommitError` | A commit is still `incomplete` after every `commit_attempts` allowed |
| `ManifestRefusalError` | Manifest resolution (below) refused one or more images; nothing is resolved for any of them |
| `VerificationRefused` (`xio_parallax_client.verification`) | The verifier cannot check a record at all (below) |

Match `ParallaxProblem` on `.slug` (for example `"sequences-not-enabled"`, or use
`SequencesNotEnabled` directly) rather than on status alone, since more than one refusal shares a
status code.

## The verifier

`AttributionVerifier(trust_roots).verify(record, original_image_bytes=None)` recomputes a
published record's hashes, checks its Ed25519 signatures and chains its leaf certificate to pinned
roots, returning a `VerificationReport` (`xio_parallax_client.verification`) of one
`VerificationCheck` (`name`, `outcome`, `detail`) per check, never a bare boolean:

- `originalImageHash`, `contentHash` (needs `original_image_bytes`; `NOT_PERFORMED` without it)
- `manifestHash:<kind>`, `manifestSignature:<kind>` — one pair per manifest
- `collectionSignature`, `imageSignature`, `leafKeyMatchesPublicKey`, `certificateChain`

`CheckOutcome` is `PASSED`, `FAILED`, `NOT_RECOMPUTABLE` (a JSON-form manifest's hash: its stored
bytes are the carrier's own JUMBF, which the record does not return — never reported `PASSED`) or
`NOT_PERFORMED`. `VerificationReport.all_performed_passed` is true when every check that ran
passed, excluding `NOT_RECOMPUTABLE`/`NOT_PERFORMED`; `.passed(name)` and `.outcome(name)` read one
check by name.

`canonicalVersion` 0 (legacy, the older Forensics Lab path) is admitted alongside 2: its manifest
and collection-signature checks report `NOT_RECOMPUTABLE`/`NOT_PERFORMED`, never `PASSED`; the
image signature, leaf key and certificate chain checks are unaffected.

`AttributionVerifier(...)` and `.verify(...)` raise `VerificationRefused` for: no trust roots; a
record with no verification block; a canonical version other than 0 or 2; a hash algorithm other
than BLAKE3-256; a signature algorithm other than Ed25519; or a content hash that is not a 32-byte
hex digest.

`TrustRoots` (never empty; `xio_parallax_client.verification`):

- `TrustRoots.from_orbital(orbital_base_url, client=None)` / `.from_orbital_async(...)` — GETs
  `{orbital_base_url}/info` anonymously and pins its `pinnedRoots` PEM array; raises
  `VerificationRefused` on a missing or empty `pinnedRoots` ("Control not activated"), and
  propagates an HTTP error as an `httpx` exception.
- `TrustRoots.from_pem(pems)` / `.from_pem_file(path)` — pins certificates from PEM strings or a
  file; raises `VerificationRefused` if none is found.

## Embedded JUMBF and C2PA

The client, never the API, looks inside a file.

`detect_embedded_c2pa(data)` recognises the carrier by signature (JPEG APP11 — possibly several
box instances, reassembled in document order; PNG `caBX`; WebP `C2PA` chunk; classic TIFF/DNG tag
`0xCD41` — each carrying at most one) and extracts and classifies every embedded JUMBF manifest
store: the C2PA manifest-store UUID and label `c2pa` make it kind `c2pa` (sent as
`application/c2pa`); any other well-formed store is kind `jumbf` (`application/jumbf`). Returns
`EmbeddedC2paResult` (`carrier`, `outcome`, `stores`, `detail`); `outcome` is `FOUND`, `ABSENT`,
`MALFORMED` (a store the JUMBF walk refuses, or two stores of one kind) or `UNSUPPORTED` (an
unrecognised carrier — nothing is said about its content; BigTIFF is explicitly unsupported).

`as_manifest_part(store)` turns a detected store into a `ManifestPart` of its classified kind and
form, to attach explicitly.

`compare_with_record(store, record)` compares a detected store's BLAKE3-256 against the declared
hash of each of the record's `jumbf`-form manifests (never `json`-form; accepts either a generated
`PublishedRecordResponse` or its plain JSON dict): `MATCH` (`matched_kind` set), `MISMATCH`,
`ABSENT_FROM_RECORD`, or `NOT_PUBLISHED` (the record's outcome is not `published`).

**Manifest selection.** `ManifestSelection(include_embedded, sidecars=())` is what one image's user
chose: whether to include every embedded store, and which sidecars go beside it; `NO_MANIFESTS` is
the selection that registers with none. `SidecarManifest.json(name, kind, data)` /
`.json_file(path, kind)` is a JSON sidecar of a stated kind; `.jumbf(name, data)` /
`.jumbf_file(path)` is a JUMBF sidecar whose kind is classified from its own bytes at resolution —
form `C2PA` is a classification result, never a valid sidecar form, and is refused at construction.

`resolve_manifests(requests)` (a list of `ManifestRequest(image, selection)`) or
`resolve_image_manifests(image, selection)` resolves every image's parts (sidecars first in given
order, then embedded stores not already covered by a sidecar) before anything is sent. It refuses
(naming every offending image, resolving nothing) when: an image carries an embedded store and a
JUMBF sidecar is offered but the two are not byte-identical as sets; a store or sidecar is
malformed; the carrier is unrecognised while the embedded store matters (`include_embedded`, or
any JUMBF sidecar given); or two manifests share one kind. Inclusion is always the caller's own
selection — the register calls send exactly what was resolved, never a client-side default.

## The PX Frame codec extension point

The sequence conversation reads and writes the PX Frame wire format through one seam,
`PxFrameCodec` (`xio_parallax_client.frames`), a `runtime_checkable` `Protocol`. Both clients
resolve it once, at construction, via `frame_codec=`: pass an instance implementing the protocol,
or leave it `None` to get the built-in pure-Python binding. A non-`None` codec that does not
satisfy the protocol raises `TypeError` naming every missing member.

A conforming implementation provides:

| Member | Signature |
| --- | --- |
| `format_version` | `int` property — the one format version this binding reads and writes |
| `encode(header, buckets)` | `(PxFrameHeader, Sequence[PxBucketContent]) -> EncodedPxFrame`; raises `PxFrameEncodeError` for input the reader would refuse |
| `decode(frame)` | `(bytes) -> PxFrameReadResult` (`PxFrameAccepted \| PxFrameRefused`) — reads exactly one frame, checking the format's rules in order |
| `build_chain(members)` | `(Collection[PxChainMember]) -> PxChainBuildResult` (`PxChainBuilt \| PxChainRefused`); raises `ValueError` for an empty member set or a member whose own links break its frame type's order |
| `compute_sequence_hash(body_frame_hashes)` | `(Sequence[bytes]) -> bytes` — BLAKE3-256 over the hashes concatenated in order; raises `ValueError` for an empty list or a hash not 32 bytes |

Every method is synchronous and keeps no state between calls. `xio_parallax_client.frames` also
exports the frozen header/result types (`PxHeadHeader`, `PxBodyHeader`, `PxEndHeader`,
`PxGapHeader`, `PxBucketContent`, `PxChainMember`, etc.) a codec's methods take and return.

## Account-side inputs the integrator supplies

None of these carry a client-side default; the client refuses rather than guess:

- `ParallaxClientOptions.account_token` — required for any authenticated call.
- `ParallaxClientOptions.batching` (`UploadBatching.max_request_bytes`/`max_images_per_request`) —
  required by `register_batch`/`lookup_batch`; the server's per-request caps are not in the
  OpenAPI document.
- `SequenceRegisterOptions.batching` (`SequenceBatching.max_request_bytes`/
  `max_frames_per_request`) — same reason, for sequence frame uploads.
- `RecordWaitOptions.poll_interval`/`poll_timeout` and `RegisterBatchOptions.poll_interval`/
  `poll_timeout` — how long to wait between polls and before giving up; only the caller knows what
  is reasonable.
- `SequenceRegisterOptions.poll_interval`/`commit_attempts` — the same, for a sequence's commit
  retries.
- Trust roots for `AttributionVerifier` — Orbital's base URL or a PEM file, one of the two.
