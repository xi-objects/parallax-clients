"""The synchronous XI Parallax client.

Wraps a generated `AuthenticatedClient` (`.api`), configured with the base URL, the bearer
account token and the admin key as an extra header when set, and reuses its httpx client for the
hand-written multipart calls the generator cannot express. Every piece of pure logic (hashing,
batching, multipart assembly, problem parsing, poll-state decisions) lives in `hashing.py`,
`multipart.py`, `problems.py` and `slots.py`; the helpers this class shares with
`AsyncParallaxClient` live in `_calls.py`, and the async mirror itself lives in `async_client.py`.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Sequence

import httpx

from . import multipart, problems
from . import slots as slots_module
from ._calls import ProgressCallback, T, _build_api, _parsed, _poll_for_record, _poll_slot_progress, _require_batching
from .frames.binding import resolve_frame_codec
from .frames.protocol import PxFrameCodec
from .generated.api.lookup import (
    get_lookup_slots_lookup_slot_id_progress,
    get_lookup_slots_lookup_slot_id_results,
    post_lookup_slots,
    post_lookup_slots_lookup_slot_id_queries_missing,
)
from .generated.api.records import get_records_original_image_hash, post_records
from .generated.api.registrations import delete_registrations_registration_id
from .generated.api.shared import get_health
from .generated.api.slots import (
    get_slots_slot_id_progress,
    post_slots,
    post_slots_slot_id_commit,
    post_slots_slot_id_uploads_missing,
)
from .generated.api.usage import get_account_stats
from .generated.models import (
    AccountStatsResponse,
    HealthResponse,
    LookupResponse,
    LookupResultsResponse,
    PublishedRecordResponse,
    PublishedRecordsRequestBody,
    PublishedRecordsResponse,
    RegisterSingleResponse,
    ResumeRequestBody,
    SlotUploadResponse,
)
from .multipart import ImageUpload, ManifestPart
from .options import ParallaxClientOptions
from .sequences.routes import SequenceRoutes
from .slots import (
    LookupBatchOptions,
    LookupBatchResult,
    RecordWaitOptions,
    RegisterBatchOptions,
    RegisterBatchResult,
    RegistrationItem,
)


class ParallaxClient(SequenceRoutes):
    """Synchronous client for the XI Parallax REST API.

    Wraps the generated `AuthenticatedClient` (`.api`) with the things a generator cannot give:
    multipart parts named `manifest[<kind>]`, typed `ParallaxProblem` refusals, the slot
    conversations as one call each, and the sequence route members (`SequenceRoutes`).
    """

    # PC-113: frame_codec resolved once, through resolve_frame_codec, and held as client.frame_codec
    def __init__(
        self,
        options: ParallaxClientOptions,
        httpx_client: httpx.Client | None = None,
        *,
        frame_codec: PxFrameCodec | None = None,
    ) -> None:
        self.options = options
        self.api = _build_api(options)
        self.frame_codec = resolve_frame_codec(frame_codec)
        if httpx_client is not None:
            self.api.set_httpx_client(httpx_client)

    def _http(self) -> httpx.Client:
        """Return the reused httpx client the generated `AuthenticatedClient` carries."""
        return self.api.get_httpx_client()

    # -- single-shot calls --------------------------------------------------------------------

    def register(self, image: ImageUpload, manifests: Sequence[ManifestPart] = ()) -> RegisterSingleResponse:
        """Register one image with its manifests in a single call (`POST /registrations`)."""
        parts = multipart.build_registration_parts(manifests, image)
        response = self._http().post("/registrations", files=parts)
        problems.raise_for_problem(response)
        return RegisterSingleResponse.from_dict(response.json())

    def lookup(self, image: ImageUpload) -> LookupResponse:
        """Find matches for one image in a single call (`POST /lookup`)."""
        parts = multipart.build_lookup_parts([image])
        response = self._http().post("/lookup", files=parts)
        problems.raise_for_problem(response)
        return LookupResponse.from_dict(response.json())

    def get_record(self, original_image_hash: str) -> PublishedRecordResponse:
        """Recover the published record for one original image hash (`GET /records/{hash}`)."""
        response = get_records_original_image_hash.sync_detailed(
            original_image_hash=original_image_hash, client=self.api
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    def wait_for_record(self, original_image_hash: str, options: RecordWaitOptions) -> PublishedRecordResponse:
        """Poll `get_record` until its outcome is terminal; raise once `options.poll_timeout` elapses."""
        return _poll_for_record(self.get_record, original_image_hash, options)

    def get_records(self, hashes: Sequence[str]) -> PublishedRecordsResponse:
        """Recover the published records for several original image hashes (`POST /records`)."""
        body = PublishedRecordsRequestBody(original_image_hashes=list(hashes))
        response = post_records.sync_detailed(client=self.api, body=body)
        problems.raise_for_problem(response)
        return _parsed(response)

    def unregister(self, registration_id: str) -> None:
        """Take a registration down (`DELETE /registrations/{id}`)."""
        response = delete_registrations_registration_id.sync_detailed(
            registration_id=uuid.UUID(registration_id), client=self.api
        )
        problems.raise_for_problem(response)

    def account_stats(self) -> AccountStatsResponse:
        """Read the calling account's grant usage (`GET /account/stats`)."""
        response = get_account_stats.sync_detailed(client=self.api)
        problems.raise_for_problem(response)
        return _parsed(response)

    def health(self) -> HealthResponse:
        """Check the service's health (`GET /health`, anonymous)."""
        response = get_health.sync_detailed(client=self.api)
        problems.raise_for_problem(response)
        return _parsed(response)

    # -- slot conversations -------------------------------------------------------------------

    def register_batch(
        self,
        items: Sequence[RegistrationItem],
        options: RegisterBatchOptions,
        on_progress: ProgressCallback | None = None,
    ) -> RegisterBatchResult:
        """Run one registration slot conversation to completion.

        Opens a slot (or resumes `options.existing_slot_id`), declares every item's hash, uploads
        only what the slot is missing in batches under `ParallaxClientOptions.batching`, commits,
        and polls `progress` until no entry is left `retry`.
        """
        batching = _require_batching(self.options, "register_batch")

        if options.existing_slot_id is not None:
            slot_id = options.existing_slot_id
        else:
            opened = self._with_503_retry(lambda: post_slots.sync_detailed(client=self.api), options.poll_timeout)
            slot_id = _parsed(opened).slot_id

        hash_to_item = slots_module.hash_registration_items(items)
        missing = self._with_503_retry(
            lambda: post_slots_slot_id_uploads_missing.sync_detailed(
                slot_id=slot_id, client=self.api, body=ResumeRequestBody(hashes=list(hash_to_item.keys()))
            ),
            options.poll_timeout,
        )
        missing_hashes = _parsed(missing).missing

        outcomes = []
        for batch in slots_module.plan_registration_batches(missing_hashes, hash_to_item, batching):
            parts = multipart.build_upload_parts([(hash_to_item[h].manifests, hash_to_item[h].image) for h in batch])
            response = self._with_503_retry(
                lambda parts=parts: self._http().post(f"/slots/{slot_id}/uploads", files=parts),
                options.poll_timeout,
            )
            outcomes.extend(SlotUploadResponse.from_dict(response.json()).outcomes)

        committed = self._with_503_retry(
            lambda: post_slots_slot_id_commit.sync_detailed(slot_id=slot_id, client=self.api), options.poll_timeout
        )
        commit = _parsed(committed)

        final_progress = _poll_slot_progress(
            lambda: get_slots_slot_id_progress.sync_detailed(slot_id=slot_id, client=self.api), options, on_progress
        )

        return RegisterBatchResult(
            slot_id=slot_id, commit=commit, final_progress=final_progress, upload_outcomes=outcomes
        )

    def lookup_batch(
        self,
        images: Sequence[ImageUpload],
        options: LookupBatchOptions,
        on_progress: ProgressCallback | None = None,
    ) -> LookupBatchResult:
        """Run one look-up slot conversation to completion; the `/lookup/slots` mirror of `register_batch`.

        A look-up commit is terminal and answers the results directly, so this call never polls
        for them: it reads `progress` once, right after commit, purely to report it, and reads
        `results` only if the commit response body came back empty. Two inputs with identical
        bytes declare and upload one hash once; the results, keyed by hash, carry that hash once.
        """
        batching = _require_batching(self.options, "lookup_batch")

        if options.existing_lookup_slot_id is not None:
            lookup_slot_id = options.existing_lookup_slot_id
        else:
            opened = self._with_503_retry(lambda: post_lookup_slots.sync_detailed(client=self.api), None)
            lookup_slot_id = _parsed(opened).lookup_slot_id

        hash_to_image = slots_module.hash_images(images)
        missing = self._with_503_retry(
            lambda: post_lookup_slots_lookup_slot_id_queries_missing.sync_detailed(
                lookup_slot_id=lookup_slot_id,
                client=self.api,
                body=ResumeRequestBody(hashes=list(hash_to_image.keys())),
            ),
            None,
        )
        missing_hashes = _parsed(missing).missing

        for batch in slots_module.plan_lookup_batches(missing_hashes, hash_to_image, batching):
            parts = multipart.build_lookup_parts([hash_to_image[h] for h in batch])
            self._with_503_retry(
                lambda parts=parts: self._http().post(f"/lookup/slots/{lookup_slot_id}/queries", files=parts),
                None,
            )

        commit_response = self._with_503_retry(
            lambda: self._http().post(f"/lookup/slots/{lookup_slot_id}/commit"), None
        )
        results = LookupResultsResponse.from_dict(commit_response.json()) if commit_response.content else None
        if results is None:
            fetched = self._with_503_retry(
                lambda: get_lookup_slots_lookup_slot_id_results.sync_detailed(
                    lookup_slot_id=lookup_slot_id, client=self.api
                ),
                None,
            )
            results = _parsed(fetched)

        progress_response = self._with_503_retry(
            lambda: get_lookup_slots_lookup_slot_id_progress.sync_detailed(
                lookup_slot_id=lookup_slot_id, client=self.api
            ),
            None,
        )
        final_progress = _parsed(progress_response)
        if on_progress is not None:
            on_progress(final_progress)

        return LookupBatchResult(lookup_slot_id=lookup_slot_id, results=results, final_progress=final_progress)

    # -- shared plumbing ----------------------------------------------------------------------

    def _with_503_retry(self, call: Callable[[], T], poll_timeout: float | None) -> T:
        """Call `call`, retrying once after `Retry-After` on a 503; any other non-2xx raises immediately.

        `poll_timeout` caps the retry wait when given; `None` waits out `Retry-After` as sent, for
        the calls, such as a look-up slot conversation, that carry no poll budget of their own.
        """
        response = call()
        if 200 <= int(response.status_code) < 300:
            return response
        problem = problems.problem_from_response(response)
        wait = problems.resolve_retry_wait(problem, poll_timeout)
        if wait is None:
            raise problem
        time.sleep(wait)
        response = call()
        if 200 <= int(response.status_code) < 300:
            return response
        raise problems.problem_from_response(response)
