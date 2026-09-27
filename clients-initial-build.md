# XI Parallax REST clients

The design of record for this repository: the two client SDKs (.NET and Python) of the XI Parallax
REST API, generated from the API's OpenAPI document, with a thin hand-written layer for what a
generator cannot give. Its `## decisions` section carries the owner's rulings; everything above it
is the brief and the survey the plan was cut from. The API this repository's clients call has its
own design of record documenting its own build.

## the brief (owner, 2026-09-22)

1. Clients. Generate, don't hand-write: the OpenAPI document now declares the whole contract, so
   the .NET and Python clients come from it (Kiota or NSwag for .NET, openapi-python-client for
   Python), regenerated when the document changes, with a thin hand-written layer for the three
   things a generator can't give: the multipart with `manifest[<kind>]` parts, the slot
   conversations as one call each (open, upload with resume, commit, poll), and verification of the
   recovered attribution: recompute the hashes, check the per-manifest, collection and image
   signatures, chain the certificate to the trust root. That verifier is the piece that makes
   "source of attribution truth" real for an integrator, and it's the same math the e2e suite
   already does. A public git repo with the two clients, a CI that regenerates from the live
   document, and the docs' getting-started walk as the client's first example.

2. C2PA detection. The client, not REST. REST's custody model is that it hashes bytes and hands
   them to the engine, and never inspects a file's content; parsing an embedded C2PA store
   server-side would make REST read into the image, and it would also make REST guess what the
   registrant wants published. Manifests are what the registrant chooses to attach, so the client
   detects an embedded manifest, shows it, and offers to attach it explicitly. The same code serves
   the other direction: when someone finds an image, the client extracts its embedded C2PA and
   compares it with the recovered record.

Start with the clients; the verifier inside them is what the C2PA comparison needs anyway.

## the contract as surveyed (2026-09-22)

Read off the API's own repository at its tree of 2026-09-22 and off the live document at
`https://api.parallax.xiobjects.com/openapi/v1.json` (build `1.0.0+acd6474`), pinned here as
`openapi/v1.json`.

### the document
- OpenAPI 3.1.1, produced at runtime by `Microsoft.AspNetCore.OpenApi` with the API's own
  transformers; served anonymously at `/openapi/v1.json` in every environment. No copy is
  committed in the API repository; the contract test there validates the served bytes.
- `servers` = `https://api.parallax.xiobjects.com`; `info.version` = semver + the build commit,
  so it changes on every deploy even when the contract does not.
- 29 paths, 35 component schemas, no `x-` extensions. Security schemes: `Bearer` (account token)
  on every product endpoint, `AdminKey` (`X-Admin-Key` header) on `/admin/*`; `/health` alone is
  anonymous.
- **No operationId on any operation.** Endpoints carry no `WithName`, so every generator either
  derives names from method + path or, for Kiota, needs none.
- **Integers are declared as `type: ["integer","string"]` with a digit pattern** (the framework's
  rendering of number-from-string reading), nullable ones as `["null","integer","string"]`. A
  generator renders these as unions rather than integers.
- Refusals are `application/problem+json` (`ProblemDetails` schema): `type` is a URN
  `urn:xio:parallax:problem:<slug>`, extensions `cap`, `registrationId`,
  `registrationRemaining`, `lookupRemaining`; `Retry-After` only on the 503
  "image could not be checked yet". 429 is lifetime-grant exhaustion, not a rate limit, per the
  published documentation's errors-and-refusals page.

### the multipart shape
- `POST /registrations`, `POST /slots/{slotId}/uploads`,
  `PUT /slots/{slotId}/entries/{imageHash}/manifests` declare a property literally named
  `manifest[<kind>]` (array of string, encoding content types `application/json`,
  `application/jumbf`, `application/c2pa`) and an `image` part (`format: binary`; single on
  `/registrations`, repeatable on slot uploads). The bracketed name is a placeholder the server
  parses by splitting on `[` and `]`; a generator cannot synthesize the real names, which is the
  first hand-written piece.
- Kind: 1 to 64 characters of `A-Z a-z 0-9 . _ -`, no registry of kinds; the part's own
  Content-Type gives the form, with no default. The manifests of an image precede its `image`
  part; per image at most a configured maximum number of manifests, per part at most a configured
  maximum manifest size — operator configuration, not in the document.
- Image part name is `image`; accepted media types are operator configuration (the API's own
  end-to-end suite uses `image/png` and `image/jpeg`). Look-up parts (`POST /lookup`,
  `/lookup/slots/{id}/queries`) are `additionalProperties`: the part name carries no meaning.
- Kinds seen in the API's own end-to-end suite: `xi-manifest` (JSON), `c2pa` (JUMBF), arbitrary
  `k1..k9`.
- Forms on the wire (verified on a live record 2026-09-22): the form enum has only `json` and
  `jumbf`; a part uploaded as `application/c2pa` comes back as form `jumbf`. A record's manifests
  are flat `{type, form, payload, hash, signature}`: a `json` payload is the JSON value inline, a
  `jumbf` payload is base64 of the stored bytes.

### the slot conversation (registration; look-up mirrors it under `/lookup/slots`)
- Open `POST /slots` → 201 `SlotOpenResponse(slotId, expiresAt)`, 409 when the account's open-slot
  limit is reached (`cap` extension). `GET /slots/{id}` reports `SlotResponse(slotId, status,
  entryCount, openedAt, expiresAt)`; `DELETE` abandons.
- Upload `POST /slots/{id}/uploads`: whole images per multipart call, never byte ranges. 200
  always, with per-part outcomes `SlotUploadOutcomeResponse(partIndex, fileName, accepted,
  imageHash, rejectionReason, registrationRemaining, lookupRemaining, registrationId)`.
  `imageHash` is **SHA-256 of the raw image bytes, lowercase hex**. Every upload refreshes the
  slot's TTL.
- **Resume is hash pre-declaration, not offsets:** `POST /slots/{id}/uploads/missing` with
  `ResumeRequestBody(hashes[])` returns `ResumeResponse(missing[])`, the declared hashes the slot
  does not hold, in order. A client that hashes locally, asks, and uploads only the missing ones
  resumes after any interruption. An already-registered image is refused at upload
  (`accepted:false`, the caller's own `registrationId`) and lands as `errata`: never billed, never
  reported missing.
- Commit `POST /slots/{id}/commit`, no body, synchronous → `SlotCommitResponse(slotId,
  status:"committed", entries[]{imageHash, state, registrationId, failureReason})`.
- Poll `GET /slots/{id}/progress` → `SlotProgressResponse(slotId, status, counts{total, held,
  registered, answered, failed, errata, retry}, entries[])`. Entry states: `held`, `registered`,
  `answered`, `failed`, `errata` terminal; **`retry` means the engine has not answered yet, poll
  again**; no `Retry-After` on this route. Slot statuses: open, `committed`, `abandoned`.
- Look-up results: `GET /lookup/slots/{id}/results` → `LookupResultsResponse(lookupSlotId,
  queries[]{imageHash, state, result: LookupResponse?, failureReason})`.
- Single-shot `POST /registrations` and `POST /lookup` collapse the conversation server-side.
- Reference flows: the API's own end-to-end suite exercises open, upload, commit and poll; errata
  and resume; the single-shot routes; and slot-upload resume specifically.

### the recovered attribution record and its verification
- `GET /records/{originalImageHash}` and `POST /records` (batch) return
  `PublishedRecordResponse(originalImageHash, outcome, manifests[], verification, failureReason)`;
  each manifest is `(type, form, payload, hash: hex, signature: base64)`; `verification`
  is `(contentHash, hashAlgorithm, signedAtUtc, signature, signatureAlgorithm, publicKey,
  leafCertificate, certificateChain[], leafCertificateThumbprint, trustContext, trustVersion,
  canonicalVersion, collectionSignature)`.
- **REST computes and checks none of it.** The engine that backs the API produces the whole
  verification block; REST renames fields 1:1. The canonical preimage lives in a private
  canonicalizer package that a public client cannot depend on. This repository re-implements the
  preimage from its documented layout and pins the re-implementation to a live record by test.
- Hashes (verified on a live record 2026-09-22): `hashAlgorithm` is the engine's literal
  `blake3-256` (the docs' example spells it `BLAKE3-256`; the verifiers compare
  case-insensitively); `contentHash` is BLAKE3-256 over the raw image file bytes, and
  **`originalImageHash` is that same hash in lower-case hex**, the key `GET /records/...`
  is read under. REST's own SHA-256 of the bytes (`imageHash` in the register response) appears
  nowhere in the record, and a record read under it answers `noRecordAnswered` forever; a
  register response carries both, and a look-up's `matchedOriginalImageHashes` are record keys.
  Manifest `hash` is BLAKE3-256 over
  the manifest's stored bytes: recomputable for JUMBF/C2PA-form manifests, whose payload is those
  bytes, but not for JSON-form manifests, whose stored bytes are the carrier's own JUMBF and are
  not returned.
- Signatures: `signatureAlgorithm` = `Ed25519`; `publicKey` is the raw 32-byte key, base64url
  (padding tolerated); signatures are standard base64. Canonical preimage version 2, every field
  length-prefixed with a big-endian uint16:
  - per manifest: `[0x02][len‖contentHash][len‖kind utf-8][len‖manifestHash]`;
  - collection: `[0x02][len‖contentHash][count u16][(len‖kind, len‖manifestHash) in record
    order]`, which detects a stripped manifest;
  - image (content hash): Ed25519 over the `contentHash` bytes alone, per the model's own comment.
- Chain: `leafCertificate` and `certificateChain` are PEM; `certificateChain` is ordered leaf
  first and **includes both the leaf and the root** (`[leaf, intermediate, root]`, Control
  returns the full chain); the root inside the chain is never trusted for
  being there, the walk must end at a pinned root. `trustContext` and `trustVersion` are
  metadata, not signature inputs (`xio.serializer` / `0` on the live record); the leaf subject is
  generic service metadata, per the published documentation. Leaves are
  Ed25519, `BasicConstraints` false, `KeyUsage` digitalSignature, one non-standard EKU. The image
  signature is Ed25519 over the raw content-hash bytes alone, `signedAtUtc` is wall-clock and
  never signed; `publicKey` is the raw 32-byte key, base64url without padding; signatures are
  standard base64.
- **What the API's own end-to-end suite actually proves:** the per-manifest signatures (with
  tamper rejection), the BLAKE3 recompute of JUMBF manifests, and the collection signature (with
  stripped-set rejection). It does **not** check the image signature and does **not** chain the
  certificate; nothing in the API repository does. The brief's "same math the e2e suite already
  does" holds for three of the five checks; the other two are implemented from the producing code
  (the engine and its canonicalizer, read in source) and proven against a live record.
- **Proven on production (2026-09-22):** with a beta account minted through the admin key from
  the API's key vault, every example ran against `https://api.parallax.xiobjects.com`;
  the verifier pinned the root from the production Orbital host named in the published
  documentation's publish configuration, whose anonymous
  `/info` serves one root, `CN=Institute of Provenance Root CA`, and every performed check
  passed. Production caps: `MaxImageBytes` 10485760,
  `MaxRequestBytes` 52428800, content types `image/jpeg,image/png,image/webp`.
- **Proven on a real record (2026-09-22):** the API's own end-to-end stack (the API with the
  hosted engine, a local Orbital and its dev CA) was run here, an image with a JSON and a JUMBF
  manifest registered through the Python client, and `GET /records/{originalImageHash}` captured
  as `fixtures/record/` with the root and Orbital's `/info`. Both verifiers pass every performed
  check on it: both manifest signatures, the collection signature, the image signature, the leaf
  key match and the chain to the pinned root; both languages carry that record as a conformance
  test.

### Orbital and the trust root (verified 2026-09-22)
Surveyed in the API's own end-to-end suite and in the Orbital service source, its Control module,
and the reference client library that consumes it.
- Orbital is the XIO trust infrastructure's resolution and record service and hosts the Control
  module that runs the certificate authority. REST never calls it directly; the engine does, via
  the harness's Orbital endpoint and control-token settings.
- **The roots are no secret and Orbital distributes them:** its unauthenticated discovery route
  `GET /info` returns `OrbitalInfoResponse` whose `PinnedRoots` (`IReadOnlyList<string>`) is
  "PEM-encoded root certificates that clients should pin for document/media verification. Empty
  when Control is not activated", populated from the certificate authority service's own pinned
  roots. The reference client library mirrors it as `DiscoveredOrbital.PinnedRoots`.
- The reference client library's document verifier is the reference consumer: it refreshes
  discovery (GETs `{OrbitalEndpoints}/info` anonymously), keeps the healthy Orbitals that
  returned at least one root, loads their PEMs into the verifier's in-memory pinned-roots set,
  falls back to a static roots-file-path setting (also settable on the CLI, bound by the website
  from its own configuration) when discovery fails, and validates chains offline against the pin
  from then on. The trust argument: the roots arrive over TLS once, and everything after is
  offline against the pin. An empty `PinnedRoots` (Control not activated) is a refusal for the
  verifier here, never an empty pin.
- Issuance stays behind the control token (`POST /control/pki/issue`, `/revoke`, `/retire`,
  `GET /control/pki/certificates/{keyId}`); `GET /control/pki/state/root` is the
  Sparse-Merkle-Tree state root, not the CA.
- REST binds none of this today: in the end-to-end run the root reaches the REST container by a
  read-only file mount, via the harness's Orbital endpoint and control-token settings.
- No tracked file names a public Orbital hostname; the owner shares the URL. `trustContext` and
  `trustVersion` are carried verbatim from the engine.
- An earlier reading of this survey, the same day, said no route serves the root. It was wrong:
  it read Orbital's controller without the reference client's consumer side, and is corrected
  here.

### the getting-started walk
Token check `GET /account/stats` → `GET /health` → the document at `/openapi/v1.json` → the
error shape → register `POST /registrations` (manifest + image) → find, from a different account,
`POST /lookup` → recover `GET /records/{originalImageHash}` → take down
`DELETE /registrations/{id}`. The clients' first example walks exactly this, adding the verifier
between recover and take down.

### conventions carried over from the API repository
.NET SDK `10.0.300` rollForward latestFeature, `net10.0`, nullable, warnings as errors,
`dotnet format` against `.editorconfig` (braces on every conditional, opening brace on its own
line, file-scoped namespaces, every using in `GlobalUsings.cs`), xunit, central package
management, LF line endings, and the documented code standard
for everything hand-written; the generated folders are exempt.

## the plan

### shape of the repository
```
clients-initial-build.md            this document
README.md
openapi/v1.json                     the pinned document (the server's own bytes), refreshed by hand from the live URL
openapi-python-client.yaml          the Python generator's configuration
scripts/generate.sh                 regenerates both clients from the pin (openapi-for-python.py reshapes
                                    the two look-up multipart bodies the Python generator cannot handle)
scripts/openapi-changed.py          same contract or not, ignoring the build commit in info.version
Xio.Parallax.Client.slnx            at the root
Directory.Build.props  Directory.Packages.props  NuGet.config (nuget.org only)  global.json
src/Xio.Parallax.Client/            the .NET package
  Generated/                        Kiota output, never edited, regenerated from openapi/v1.json
  Multipart/  Slots/  Verification/  Manifests/ the hand-written layer
tests/Xio.Parallax.Client.Tests/
pyproject.toml  uv.lock             at the root; hatchling, package under python/
python/xio_parallax_client/         the Python package
  generated/                        openapi-python-client output, never edited
  client.py  multipart.py  slots.py  problems.py  verification/  manifests.py
python/tests/
examples/dotnet/GettingStarted/  examples/python/getting_started.py
```

### generation
- **.NET: Kiota.** It reads OpenAPI 3.1, needs no operationIds (request builders follow the
  path: `client.Slots[slotId].Uploads.PostAsync(...)`), carries a `MultipartBody` that takes
  arbitrary part names, and is Microsoft-maintained on the current .NET. NSwag keys its method
  names on operationIds the document lacks and its 3.1 support is partial. Output is committed
  under `Generated/` with `kiota-lock.json`; the folder is marked `generated_code = true` so
  `dotnet format` and the standards leave it alone. Runtime dependencies: the `Microsoft.Kiota.*`
  packages from nuget.org only.
- **Python: openapi-python-client**, pinned in `pyproject.toml`'s dev group, driven by a
  committed `openapi-python-client.yaml`. Until the API ships operationIds it names endpoints from
  method + path; the hand-written layer is the public surface either way.
- The generated code is committed alongside the pin, so a reader of the public repository sees
  the client without running a generator and a build is reproducible from a commit; the build
  commands show when the committed output no longer matches the pin.
- Two fixes belong at the source, in the API repository, and are worth making there:
  1. stable operationIds on every endpoint (`WithName`), so both generators name methods from
     one declaration in the code (today the Python endpoint modules are named from method and
     path, such as `post_slots_slot_id_uploads`);
  2. integers declared as integers (drop the `string` alternative and the digit pattern): Kiota
     already collapses them to `int?`, but the Python client renders `int | str` and the hand
     layer normalizes.

### the hand-written layer (same shape in both languages)
1. **Multipart builder.** `ManifestPart(kind, form, bytes)` becomes the part `manifest[<kind>]`
   with Content-Type `application/json`, `application/jumbf` or `application/c2pa` from the form;
   an image becomes the part `image` with its media type; the manifests of an image precede its
   `image` part. The kind is validated against `^[A-Za-z0-9._-]{1,64}$` before anything is sent,
   and a missing form is a refusal, never a default. Look-up parts take any name.
2. **Slot conversations, one call each.**
   - `RegisterBatch(images, manifestsPerImage)`: open; hash each image (SHA-256, lowercase hex);
     `uploads/missing` with the hashes; upload only the missing ones, batched under the caller's
     stated request-byte bound (the server's caps are operator configuration, so the client takes
     them as options and refuses to guess); commit; poll `progress` until no entry is `retry`,
     with bounded backoff; return the final entries. Running the same call again over the same
     images after an interruption is the resume: it re-declares and uploads only what the slot
     lacks. `errata` entries are returned as what they are.
   - `LookupBatch(images)`: open a look-up slot; `queries` with `queries/missing` resume,
     deduplicated by hash; commit — terminal, answering `results` directly, so this never polls;
     read `progress` once, after commit, to report it.
   - `Register(image, manifests)` and `Lookup(image)` are the single-shot routes plus the builder.
   - Refusals surface as one typed problem (the `ProblemDetails` fields, the URN slug, the
     extensions, `Retry-After`); a 503 "could not be checked yet" is retried once per its
     `Retry-After`, nothing else is retried silently.
3. **The attribution verifier.** `Verify(record, originalBytes?, trustRoots)` returns a verdict
   per check, never a bare boolean:
   - hashes: `originalImageHash` must equal `contentHash` (the record is keyed by its own
     content hash in hex); `contentHash` recomputed over the original bytes by `hashAlgorithm`
     when they are given (`blake3-256` implemented, compared case-insensitively; any other name
     is a refusal naming it); each manifest's hash recomputed where its payload is its stored bytes
     (JUMBF, C2PA) and reported *not recomputable*, never *passed*, for JSON-form manifests;
   - per-manifest, collection and image signatures over the version-2 preimages above, Ed25519;
     any `canonicalVersion` other than 2 is a refusal;
   - chain: the leaf's public key must equal `publicKey`; the leaf walked through
     `certificateChain` (which carries the leaf and the root too) to a pinned root, valid at
     `signedAtUtc`. The roots are bootstrapped once from Orbital's anonymous
     `GET /info` over TLS at the configured Orbital URL and pinned in memory, exactly as the
     reference client library's verifier does, with a PEM-path option as the fallback when
     discovery fails; every later verify is offline against the pin. No root at all is a refusal,
     never a skipped check.
   - Libraries: .NET has no in-box Ed25519 (Windows CNG carries no EdDSA; the platform docs
     confirm every Ed25519 pairing throws `PlatformNotSupportedException` there), so the .NET
     verifier uses BouncyCastle.Cryptography for Ed25519 and the `Blake3` package, both nuget.org;
     Python uses `cryptography` and `blake3`. Nothing from the organisation's private Azure
     DevOps Artifacts feed, in either package, ever.
   - Conformance: one fixture record captured from the live API (with its trust root, once
     ruling 1 lands) and the API repository's own fixtures pin the preimage; a tamper, a stripped
     manifest and a wrong root each have a failing test.
4. **C2PA detection (brief 2, after the verifier ships; revised 2026-09-26).** Extract every
   embedded JUMBF manifest store from a file (a JPEG's APP11 segments, one or more box instances,
   in document order; PNG `caBX`; WebP `C2PA`; classic TIFF tag 0xCD41), show it, and classify each
   store `c2pa` or `jumbf` by the C2PA manifest-store UUID and label; classification never refuses.
   Inclusion is the registrant's selection per image, resolved over the whole collection before
   anything is sent: the embedded store(s) or not, plus JSON or JUMBF sidecars, with a JUMBF
   sidecar and an embedded store required to match byte-identically or refuse the collection. On
   the finder's side, extract the store(s) from the found file and compare each to the recovered
   record's manifests by BLAKE3 of the bytes, reporting match, mismatch, absent from the record, or
   not published. Never parsed by REST, never included without the registrant's say.

### regeneration, by hand
- No CI: nothing is shipped (ruled 2026-09-22). When the API's contract changes, the live
  document is fetched over `openapi/v1.json` and `scripts/generate.sh` regenerates both clients;
  `scripts/openapi-changed.py` says whether two documents are the same contract, ignoring the
  build commit in `info.version`. The gates are the documented build commands.

### build order
1. **Bootstrap** — solution, props, pin, both generations with their locks (done 2026-09-22).
2. **The hand-written layer in both languages** — client with bearer/admin auth, typed problems,
   the multipart builder, single shots, the slot conversations, tested against a fake server
   shaped from the pin and the e2e reference flows.
3. **The attribution verifier in both languages** — hashes, three signatures, chain against
   Orbital's pinned roots, verdicts, fixtures.
4. **Getting started** — the two examples walking the docs' sequence with the verifier between
   recover and take down; README.
5. **C2PA detection and comparison** — brief 2, at the bytes level (done 2026-09-22; proven
   live: attach then MATCH, not attach then ABSENT_FROM_RECORD).
6. **At the source** — operationIds and strict integers in the API repository, when convenient.
7. **Sequences** — the .NET client's frame-by-frame conversation and `ISequenceFrameSource`, the
   interface later ingestion implements, proven by a stand-in directory-of-images example
   (done 2026-09-26; see `## sequences (2026-09-26)` below).

## decisions (owner rulings, 2026-09-22)

### ruled by the owner
- **Generate, never hand-write** the clients; the hand-written layer is exactly the three pieces
  the brief names (multipart with `manifest[<kind>]`, the slot conversations as one call each,
  the attribution verifier) and, later, the C2PA detection.
- **Python comes from openapi-python-client; .NET comes from Kiota** (ruled 2026-09-22 when
  asked, over NSwag: it reads the API's OpenAPI 3.1.1, needs no operationIds, and its multipart
  body takes arbitrary part names).
- **C2PA detection lives in the client, never in REST** (revised 2026-09-26: REST requires only
  well-formed JUMBF, never that JUMBF be C2PA; the client classifies a well-formed store `c2pa` or
  `jumbf` and never refuses on that account), and a detected store is included only when the
  registrant's selection says so.
- **Public git repository, the docs' getting-started walk as the first example.** The brief's
  "CI that regenerates from the live document" was superseded the same day by the no-CI ruling
  below: regeneration is a command run by hand when the contract changes.
- **Order:** the clients first, the verifier before the C2PA comparison that needs it.
- **No remote yet:** the GitHub repository and the XI Objects credentials come later; this tree is
  instantiated locally and nothing is pushed.
- **GitHub home (2026-09-22):** an XI Objects organization, repository `parallax-clients`.
- **Distribution: source only (ruled 2026-09-22).** Nothing goes to NuGet, PyPI or any registry.
  Integrators clone or submodule the repository, reference the .NET project and install the Python
  package from the tree; no package metadata, no pack step, no release workflow.
- **Trust root (2026-09-22):** integrators obtain it from Orbital, the roots being no secret.
  Verified: Orbital's anonymous `GET /info` returns the pinned roots as PEM, and the reference
  client library's verifier already bootstraps from it (see "Orbital and the trust root"). The
  owner shares the Orbital URL the clients point at. The clients do exactly what that library
  does: fetch the roots once from `/info` over TLS, pin them in memory, verify offline from then
  on.
- **Package identifiers (ruled 2026-09-22, revised the same day):** `Xio.Parallax.Client` for .NET
  (namespace and NuGet id) and `xio-parallax-client` for Python (module `xio_parallax_client`);
  the prefix is kept because it collides less if the packages ever go public.
- **The generated code is committed with the pin (ruled 2026-09-22):** `openapi/v1.json` and
  both generated folders are in the repository, regenerated by hand from the pin when the
  contract changes.
- **Default branch `main` (ruled 2026-09-22).**
- **C2PA at the bytes level (ruled 2026-09-22):** the clients locate the embedded manifest store
  per carrier (JPEG APP11, PNG `caBX`, WebP `C2PA`, TIFF tag 0xCD41), list its JUMBF boxes, attach
  it only when the registrant says so, and compare a found file's store with the recovered record
  by BLAKE3 of the bytes, exactly as the API treats a manifest: opaque bytes. No C2PA library, no
  claim decoding, no COSE validation; an unrecognised carrier is reported as unsupported, never as
  "no C2PA". **Superseded in part by the 2026-09-26 rulings below:** a store need only be
  well-formed JUMBF, never C2PA specifically; a JPEG may carry several box instances; and
  attaching is now a resolved selection governed by the conflict rule, not a bare yes/no.
- **No CI (ruled 2026-09-22):** nothing is shipped, so no workflow runs; regeneration and the
  gates are commands run by hand.
- **Roots straight from Orbital (ruled 2026-09-22):** the clients fetch `pinnedRoots` from
  Orbital's anonymous `GET /info` once over TLS at the configured Orbital URL, pin them in
  memory and verify offline, with a PEM file as the fallback, exactly as the reference client
  library does; no REST relay. The Orbital URL is configuration the owner supplies.
- **Legacy canonical version 0 admitted (ruled 2026-09-23):** production records registered
  through the older Forensics Lab path carry `canonicalVersion: 0` and were refused outright,
  failing the badge on every such article image. Proven empirically (Python `cryptography`) that
  the image signature still verifies Ed25519 over the raw `contentHash` bytes, exactly as version
  2's does, so both verifiers now admit version 0 alongside version 2 (any other version stays a
  refusal) and run that same check, the leaf-key match and the certificate chain normally; since
  neither verifier implements a version-0 manifest/collection canonical preimage, those checks
  report not-recomputable (or not-performed when the record declares no value), never passed.
  `hashAlgorithm` was already compared case-insensitively, covering the legacy lower-case
  `blake3-256`. Fixture: `fixtures/record-legacy/` (a real production record, `canonicalVersion: 0`,
  `contentHash` upper-case hex, one `c2pa` manifest with `hash`/`signature` null); its chain ends
  at `CN=Institute of Provenance Root CA`, so `fixtures/record-legacy/orbital-info.json` was
  captured from production Orbital's own `/info` rather than reusing the dev root in
  `fixtures/record/`.
- **REST validates JUMBF, not C2PA (ruled 2026-09-26):** REST validates that a manifest is
  well-formed JUMBF and rejects invalid JUMBF; it does not require that a JUMBF manifest be C2PA,
  and anyone's own JUMBF spec is kept. The client's box walk is extraction plus a local preflight
  over the whole collection, never stricter than the JUMBF box grammar. Partly supersedes "C2PA at
  the bytes level (ruled 2026-09-22)", which spoke only of the embedded C2PA store.
- **Classification, not gatekeeping (ruled 2026-09-26):** the C2PA manifest-store UUID and the
  label `c2pa` classify a well-formed store as kind `c2pa` (sent as `application/c2pa`) and every
  other well-formed store as kind `jumbf` (sent as `application/jumbf`); the classification never
  refuses. The server stores both forms as `jumbf`.
- **Several JUMBF instances per JPEG (ruled 2026-09-26):** a JPEG may carry several JUMBF box
  instances in APP11: every well-formed one is a manifest under its kind, in document order; two
  of the same kind refuse naming the count. A malformed instance makes the detection Malformed.
  PNG, WebP and TIFF hold at most one, as ruled 2026-09-22.
- **Inclusion is the integrator's selection (ruled 2026-09-26):** the client detects, shows and
  classifies; inclusion is the integrator's own selection per image: include the embedded
  block(s) or not, plus sidecars, each JSON (kind stated) or JUMBF (classified by its own bytes);
  none is neither. The register calls send exactly the list they are given. Partly supersedes
  "C2PA detection lives in the client, never in REST", whose "attached only when the registrant
  chooses to" is now this selection, not a bare yes/no.
- **The conflict rule (ruled 2026-09-26):** when an image carries an embedded block and a JUMBF
  sidecar is offered, the two must be byte-identical (with several blocks or sidecars, the two
  sets must match exactly); identical bytes are one manifest, included once; anything else
  refuses. Whenever the embedded block matters (include embedded, or any JUMBF sidecar given): a
  malformed block refuses, an unrecognised carrier refuses (the client cannot say whether a block
  is there and never skips the check), a supported carrier with no block contributes nothing. Two
  manifests of one kind on one image refuse. A JSON sidecar never conflicts with an embedded
  block. Supersedes in part "C2PA at the bytes level (ruled 2026-09-22)"'s "attach it only when
  the registrant says so".
- **Whole-collection resolution (ruled 2026-09-26):** resolution runs over every item of a
  collection before anything is sent; any refusal refuses the whole collection with every
  offending item listed, and nothing is returned partially.
- **Names keep their C2PA history (ruled 2026-09-26):** type, namespace and module names keep
  their C2PA names; the words say "embedded JUMBF manifest store, classified c2pa or jumbf."

### design facts that follow from the rulings
- Verdicts, not booleans, from the verifier; refusals, not skips, for an unknown hash
  algorithm, canonical version, or a missing trust root.
- Cryptography from public feeds only: BouncyCastle.Cryptography and Blake3 on nuget.org;
  `cryptography` and `blake3` on PyPI.
- Server caps are the caller's options: request-byte, image-byte and manifest caps are the
  operator's configuration and not in the document, so the batching client takes them as options
  and refuses to batch without them rather than guessing.
- One repository, one root solution and one root `pyproject.toml`; the Python package's sources
  live under `python/` through hatchling's package mapping.

## sequences (2026-09-26)

The .NET client's sequence conversation: the API's frame-by-frame registration route, alongside
the batch and single-shot conversations the rest of this file covers. .NET only for now; the
Python client is untouched, and no parity between the two is required while sequences are under
active development. `xio_parallax_rest`'s `sequences-initial-build.md` (rulings S1-S19) is the
design of record for the sequence workflow itself; this section is this repository's design of
record for the client that consumes it, superseding the standalone `sequences-design.md` note it
was cut from (removed once this section landed).

### the brief (owner, 2026-09-26)

The client must support the sequence workflow the API now serves. HOW video is decoded into
distinct frames is set down for later; this build cuts the internal service layer and the
interface a later ingestion implements, proven by a stand-in example that reads a directory of
already-decoded image files as one sequence's frames.

### the contract as surveyed (2026-09-26, live document 1.0.0+29a207a)

- `POST /sequences` (multipart: optional `expectedSize`, `manifest[<kind>]` parts as the slot
  routes take them) -> 201 `SequenceOpenResponse { sequenceId, headFrame (the HEAD frame, base64),
  ticket }`. The account's `sequences_enabled` gate answers 403 otherwise.
- Every other route carries the header `X-Sequence-Ticket: <ticket>` (required).
- `POST /sequences/{id}/frames` (multipart: one or more file parts, any part name, each one PX
  BODY or END frame's bytes as `application/octet-stream`; the server reads only parts whose
  Content-Disposition carries a file name, in request order; the whole request's Content-Length
  bounded by the account's `maxRequestBytes`, 413 otherwise) -> 201
  `SequenceFrameBatchResponse { frames [{frameId, errata}], verdict? }`; the verdict is present
  when the batch sealed the sequence. All or nothing. 409 for a state the sequence refuses, 422
  when an image could not be checked, 503 when no engine is configured.
- `DELETE /sequences/{id}/frames/{frameId}` -> 204 (open only).
- `GET /sequences/{id}/gaps` -> `SequenceGapsResponse { gaps [{from, to, gapFrame}] }`.
- `GET /sequences/{id}/progress` -> `SequenceVerdictResponse { state, framesReceived,
  expectedSize?, reach, gaps [{from, to}], errata [{frameId, originalImageHash}], connected }`.
- `PUT /sequences/{id}/expected-size` `{ expectedSize }` -> 204.
- `POST /sequences/{id}/commit` -> 200 `SequenceCommitResponse { sequenceHash?, outcome
  (registered | alreadyRegistered | incomplete), sequenceRecordPublished, frames [{frameId, state,
  originalImageHash?, refusalName?}] }`; 409 with the shortfalls when not committable;
  `incomplete` is retried by calling commit again (the server resumes from the first unpublished
  frame, S12).
- `GET /sequences/{id}/results` -> 200 `SequenceResultsResponse { sequenceHash, outcome, finalSize,
  committedAt }`; 409 before commit.
- `DELETE /sequences/{id}` -> 200 `SequenceAbandonResponse { sequenceId, state, packetsPurged }`.

The frame model (Xio.Parallax.Common 0.1.1 on nuget.org): HEAD (minted by REST, frame id 0), BODY
(client, `PxBodyHeader(sequenceId, frameId, prev, next, sourceTimeOffsetMicroseconds)` plus
buckets, the image under `PxFrameConstants.ImageBucketTag` "IMAG"), END (client,
`PxEndHeader(sequenceId, frameId, prev)`), GAP (REST only). Frame ids are longs the client owns:
monotone along the chain, every BODY's prev below its id and next above it, contiguity never
required. `IXioPxFrameEncoder.EncodeAsync(XioEncodePxFrameRequest(header, buckets))` answers the
frame bytes and the frame hash; `IXioPxFrameDecoder.DecodeAsync` reads one back (the HEAD from
open is decoded, never assumed to be id 0).

### the shape

One domain, `Sequences/`, in `src/Xio.Parallax.Client` with `Models|Interfaces|Enums|Services` and
namespaces following folders, built exactly as `Slots/` is: generated request builders under the
hand-written layer, `ParallaxClient` partial classes, sealed records, typed problems through the
existing `ExecuteAsync` and `ParallaxProblemException`, the multipart sender the slot upload uses,
required options with no client-side default for any server cap.

1. **The generated surface.** `openapi/v1.json` replaced by the live document and the .NET client
   regenerated with Kiota 1.35.0 (`kiota generate` line of `scripts/generate.sh`; the Python half
   of that script not run and `python/` not touched). `Xio.Parallax.Common` 0.1.1 (nuget.org,
   pulling Xio.Crypto 1.0.8 from nuget.org) joins `Directory.Packages.props` and the client
   project. Package version 0.4.0.
2. **The frame source: the interface later ingestion implements.** `ISequenceFrameSource` —
   `IAsyncEnumerable<SequenceFrameInput> ReadFramesAsync(CancellationToken)` yielding frames in
   chain order. `SequenceFrameInput(long FrameId, TimeSpan SourceTimeOffset,
   IReadOnlyList<PxBucketContent> Buckets)` with a factory `ForImage(frameId, offset, imageBytes)`
   that puts the bytes under the image bucket tag. The source owns the ids (monotone, room
   allowed) and says nothing about links: the client derives prev from the previous frame it read
   (the HEAD's id for the first) and next from the following one (END's id for the last),
   buffering one frame of lookahead. A source that yields a non-monotone id is refused, naming the
   id, before that frame (or any batch holding it) is sent; batches before it may already have
   been uploaded, exact retransmits being harmless on a later run.
3. **The route members** on `ParallaxClient` (`Sequences/Services/ParallaxClient.Sequences.cs`),
   one per operation, each one call: `OpenSequenceAsync(SequenceOpenRequest)` (manifests as
   `ManifestPart`s through the existing multipart builder, optional expected size) returning
   `OpenedSequence(Handle, HeadFrameId)` with the HEAD decoded through Common;
   `UploadSequenceFramesAsync(SequenceHandle, IReadOnlyList<EncodedFrame>)` (each frame one
   `application/octet-stream` file part, part name its id, file name `<frameId>.px`);
   `RemoveSequenceFrameAsync`; `GetSequenceGapsAsync`; `GetSequenceProgressAsync`;
   `AmendSequenceExpectedSizeAsync`; `CommitSequenceAsync`; `GetSequenceResultsAsync`;
   `AbandonSequenceAsync`. `SequenceHandle(SequenceId, Ticket)` carries the ticket; the header is
   set once, in one place, for every call. The ticket never reaches a log or an exception.
4. **The conversation, one call**: `RegisterSequenceAsync(ISequenceFrameSource source,
   SequenceRegisterOptions options, IProgress<SequenceVerdictResponse>? progress, ct)`: open (or
   resume through `options.Existing`), read the source, encode each BODY through Common with its
   links, upload in batches under `options.Batching` (`MaxRequestBytes`, bounding the whole
   multipart body each request sends, part headers, boundaries and closing delimiter included,
   and `MaxFramesPerRequest`, both required; a frame whose request alone exceeds
   `MaxRequestBytes` is refused, naming it, before it or any batch holding it is sent), encode END
   (id = the last BODY id + 1, prev = the last BODY id) and upload it as the sealing batch, take
   the verdict it answers (an END batch answered without one did not seal, and is refused naming
   the END id): not connected, any gap or any errata refuses with the verdict (typed
   `SequenceVerdictException` carrying it) and nothing is committed; then commit, repeating while
   the outcome is `incomplete` up to `options.CommitAttempts` with `options.PollInterval` between
   attempts, then results. Returns `SequenceRegisterResult(Sequence, Verdict, Commit, Results)`,
   `Sequence` the `OpenedSequence` the conversation ran in. Resume: `options.Existing` (the
   `OpenedSequence` a first run answered: handle and HEAD id) reads progress and gaps first; when
   the state is open the source is read again and only frames whose id lies in a gap or above the
   reach are uploaded, then END; when sealed, only the gaps' fills; when committed, commit is
   called again (it resumes) and results read. An account with the feature off, a refused batch
   or a shortfall surface as the typed problem the server answered.
5. **Example** `examples/dotnet/SequenceFromImages`: a directory of image files, in name order, as
   the frame source (one image per frame, ids 1..n, the source time offset from a constant frame
   interval the example states), registered through the conversation, then the results and one
   look-up of a frame proving the round trip. It is the stand-in for the ingestion that comes
   later and the proof the interface is enough.
6. **Docs**: README gains a "Sequences" section (the interface, the conversation, resume, the
   flag), CLAUDE.md's layout line names the `Sequences/` domain and the nuget.org Common
   reference, this section itself.

### rules that bind every story

- Generated code is never edited; nothing in `python/` moves.
- No client-side default for a server cap: request bytes, frames per request, poll interval,
  commit attempts are required options; a missing one throws `ArgumentException` naming it.
- Tickets and account tokens never reach a log, an exception message or a record's ToString.
- Tests with the code: xunit, the existing `FakeHttpMessageHandler` scripting responses shaped
  from the live document, a fake `ISequenceFrameSource`; encoding through the real Common encoder;
  every acceptance criterion has a backing test; no test reads markdown.
- The gate for every story: `dotnet build Xio.Parallax.Client.slnx -c Release`,
  `dotnet format Xio.Parallax.Client.slnx --verify-no-changes`,
  `dotnet test Xio.Parallax.Client.slnx -c Release --no-build`. Nothing Python runs.
- Every change site carries its story key (PC-101 .. PC-106) in one line saying what.

### ruled by the owner

- **.NET only, for now (ruled 2026-09-26):** the sequence conversation lands in the .NET client
  only; the Python client is untouched.
- **No parity required during active development (ruled 2026-09-26):** sequences moving fast on
  the API side means the two clients are allowed to diverge until the workflow settles; the
  Python client catching up is a later, separate piece of work.
- **Xio.Parallax.Common from nuget.org (ruled 2026-09-26):** the PX frame model and its
  encoder/decoder are consumed as the published `Xio.Parallax.Common` 0.1.1 package (pulling
  Xio.Crypto 1.0.8), both from nuget.org; nothing from a private feed.
- **HOW video is decoded into frames is set down for later (ruled 2026-09-26):** this build cuts
  `ISequenceFrameSource` as the seam a later ingestion implements; the client itself never decodes
  video, and the shipped example stands in with an already-decoded directory of image files.
- **No AI or assistant attribution anywhere in this repository (ruled 2026-09-26):** no co-author
  trailer, no session line, no generated-by remark, in commit messages, code comments, docs or
  examples.
- **Errata refuse before commit (ruled 2026-09-26):** the server's commit refuses any errata frame
  (REST `SequenceCommitService`), so the client treats errata in the sealing verdict exactly as it
  treats gaps and not-connected: `RegisterSequenceAsync` throws `SequenceVerdictException`
  carrying the verdict (its message names the gap count, the errata count and whether it is
  connected) and commits nothing; the sequence stays sealed for the caller to abandon or to
  resolve through take-down. `SequenceRegisterResult` carries no errata; the exception's verdict
  carries the list.
- **Refused before the offending frame is sent (ruled 2026-09-26):** the client streams the source
  with one frame of lookahead, so a non-monotone id or an oversized frame is refused before that
  frame (or any batch holding it) is sent; batches before it may already have been uploaded,
  exact retransmits being harmless on a later run.

## sequences in python (2026-09-27)

The Python client catches up with .NET's sequence conversation above: the same nine routes, the
same one-call `register_sequence`, built as `python-sequences-design.md` worked it out in full;
this section distils that note to what stays true once the code lands. It supersedes the
2026-09-26 rulings ".NET only, for now" and "no parity required during active development" below;
those two rulings are left as written, for the record of what was decided when.

### the surveyed facts

- The pinned document's `/sequences/{sequenceId}/...` operations never declare `sequenceId`
  `in: path` (the server's ticket filter reads it from route values instead), which makes
  openapi-python-client refuse those operations with "Incorrect path templating" and skip them —
  8 of the 9 sequence operations, confirmed by a scratch generation run. Kiota tolerates the same
  document because it builds a request builder from the path template alone.
- Xio.Parallax.Common (nuget.org, .NET) has no Python counterpart; the pure-Python reimplementation
  here is proven against `xio_parallax_common`'s own test vectors, vendored at a pinned commit, not
  against the package itself.
- `blake3` is already a dependency (the attribution verifier uses it), so the codec needs none new.

### the seam

`xio_parallax_client.frames.PxFrameCodec`, a `typing.Protocol`: `format_version`, `encode`,
`decode`, `build_chain`, `compute_sequence_hash`, mirroring the five services
`AddXioParallaxCommon()` registers in .NET, folded into one object. Both clients take a
keyword-only `frame_codec` on their constructor; `None` resolves through
`frames.binding.resolve_frame_codec` to the package's own pure-Python binding
(`frames/pure/PurePxFrameCodec`), and a codec missing part of the protocol is refused, naming every
missing member. `frames/binding.py` holds the default as its one import line, so a future codec
library or native shim replaces it package-wide by changing that line, or per client through
`frame_codec=`; nothing in `sequences/`, either client, the example or the tests depends on which
binding runs, and the conformance suite runs over every binding it is given.

### the rulings

- **Python gets Sequences (ruled 2026-09-27):** superseding "the Python client is untouched" and
  "no parity required" above; the two clients converge on the sequence conversation.
- **The codec sits behind a protocol (ruled 2026-09-27):** the .NET client composes
  Xio.Parallax.Common directly with no seam of its own; the Python client, having no such package
  to compose, puts one protocol between the conversation and its pure-Python binding so a future
  library or native shim is a one-line change, never a rewrite of the conversation.
- **Admission streams; validation lists everything (ruled 2026-09-27):** frame admission mirrors
  .NET's stream-with-lookahead ruling above (the first offending frame refuses, naming it, before
  it or any batch holding it is sent); option and frame-input validation, being pure checks over
  values already in hand, list every bad field together in one refusal instead.
- **The 403 is typed in Python only (ruled 2026-09-27):** `sequences-not-enabled` builds
  `problems.SequencesNotEnabled(ParallaxProblem)`, matched by slug (a refused ticket is also 403,
  under a different slug); `except ParallaxProblem` still catches it. .NET keeps its plain
  `ParallaxProblemException` unchanged.
- **Vectors vendored, not reimplemented from a private clone (ruled 2026-09-27):** the format's
  disclosure to this repository is accepted; `xio_parallax_common`'s test vectors are copied
  unmodified into `python/tests/vectors/px-frame/` at a pinned commit, recorded in that
  directory's `VECTORS.md`, and are XI Objects' own test material redistributed as-is, not under
  this repository's MIT license; the conformance suite runs over every binding.
- **The generator gap is closed in the reshape script, not upstream (ruled 2026-09-27):**
  `scripts/openapi-for-python.py` declares, for every operation, each path-template name it does
  not already declare `in: path` as a required string parameter derived from the template itself —
  a no-op the day the server declares it directly; generated code stays untouched, and the proper
  fix (binding `sequenceId` in each handler) belongs in `xio_parallax_rest`, outside this work.

### the stories

Keys continue PR #2's PC-101..106. `python-sequences-design.md` carries each story's owned files
and acceptance criteria in full.

- **PC-107** the pure PX Frame codec (`frames/pure/`) and the binding line (`frames/binding.py`).
- **PC-108** the pure chain builder and sequence hash (`frames/pure/_chain*.py`).
- **PC-109** the vendored vectors and the conformance suite over every binding.
- **PC-110** the generator reshape declaring undeclared path parameters; all nine sequence
  operations generate.
- **PC-111** the sequence models, the frame-input validation, the wire words, the typed 403.
- **PC-112** the chain linker, batch planning, frame encoding, and sequence multipart parts.
- **PC-113** the nine route members, sync and async, and the `frame_codec` keyword on both
  clients.
- **PC-114** the one-call `register_sequence` conversation, sync and async, with resume.
- **PC-115** the Python `sequence_from_images.py` example, mirroring .NET's.
- **PC-116** this section, the README, and the version.
- **PC-117** the .NET frame-input validation catches up: bucket tag and data checked up front with
  every other frame-input field, and the encoder names the frame id when Common still refuses.

### what stays open

The licence question this note raised for the vendored vectors and for a clean-room
reimplementation from the format's own documentation is for the owner to confirm; until then,
`VECTORS.md` states the vectors' status as XI Objects' own material redistributed unmodified, and
this repository's MIT license does not extend to them.

