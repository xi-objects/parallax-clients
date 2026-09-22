# XI Parallax REST clients

Client SDKs for the XI Parallax REST API, in .NET (`Xio.Parallax.Client`) and Python
(`xio-parallax-client`), not yet published to a registry. Both are generated from the API's OpenAPI document, pinned here
at `openapi/v1.json` and refreshed by CI from the live document at
`https://api.parallax.xiobjects.com/openapi/v1.json`. On top of the generated code each package
carries a small hand-written layer:

- the multipart request with `manifest[<kind>]` parts, which the document can only describe;
- the slot conversations (open, upload with resume, commit, poll) as one call each, for
  registration and for look-up;
- the attribution verifier: it recomputes the hashes of a recovered record, checks the
  per-manifest, collection and image signatures, and chains the signing certificate to a trust
  root, so an integrator never takes the API's word for it.

## Status

Instantiated 2026-09-22, no remote yet. `clients-initial-build.md` is the design of record and
carries the plan, the surveyed contract, and the owner's rulings. The first Features build the
solution, the generation, and CI; see that document's "Features, in order".

## Building

The gate legs are the pod kit's, read off this tree: the .NET leg when the root holds one
`*.slnx`, the Python leg when it holds a `pyproject.toml`. See the build commands.
