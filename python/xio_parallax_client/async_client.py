"""The asynchronous XI Parallax client.

Async mirror of `ParallaxClient` (see `client.py`), built on the generated `AuthenticatedClient`'s
async httpx client. Shares its pure logic modules (`hashing.py`, `multipart.py`, `problems.py`,
`slots.py`) and its construction/parsing helpers (`_calls.py`) with the synchronous client.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Sequence
from typing import Any

import httpx

from . import multipart, problems
from . import slots as slots_module
from ._calls import (
    ProgressCallback,
    _build_api,
    _parsed,
    _poll_for_record_async,
    _poll_slot_progress_async,
    _require_batching,
)
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
from .sequences.async_routes import AsyncSequenceRoutes
from .slots import (
    LookupBatchOptions,
    LookupBatchResult,
    RecordWaitOptions,
    RegisterBatchOptions,
    RegisterBatchResult,
    RegistrationItem,
)


class AsyncParallaxClient(AsyncSequenceRoutes):
    """Asynchronous mirror of `ParallaxClient`, built on the generated `AuthenticatedClient`'s async httpx client."""

    # PC-113: frame_codec resolved once, through resolve_frame_codec, and held as client.frame_codec
    def __init__(
        self,
        options: ParallaxClientOptions,
        httpx_client: httpx.AsyncClient | None = None,
        *,
        frame_codec: PxFrameCodec | None = None,
    ) -> None:
        self.options = options
        self.api = _build_api(options)
        self.frame_codec = resolve_frame_codec(frame_codec)
        if httpx_client is not None:
            self.api.set_async_httpx_client(httpx_client)

    def _http(self) -> httpx.AsyncClient:
        """Return the reused async httpx client the generated `AuthenticatedClient` carries."""
        return self.api.get_async_httpx_client()

    # -- single-shot calls --------------------------------------------------------------------

    async def register(self, image: ImageUpload, manifests: Sequence[ManifestPart] = ()) -> RegisterSingleResponse:
        """Register one image with its manifests in a single call (`POST /registrations`)."""
        parts = multipart.build_registration_parts(manifests, image)
        response = await self._http().post("/registrations", files=parts)
        problems.raise_for_problem(response)
        return RegisterSingleResponse.from_dict(response.json())

    async def lookup(self, image: ImageUpload) -> LookupResponse:
        """Find matches for one image in a single call (`POST /lookup`)."""
        parts = multipart.build_lookup_parts([image])
        response = await self._http().post("/lookup", files=parts)
        problems.raise_for_problem(response)
        return LookupResponse.from_dict(response.json())

    async def get_record(self, original_image_hash: str) -> PublishedRecordResponse:
        """Recover the published record for one original image hash (`GET /records/{hash}`)."""
        response = await get_records_original_image_hash.asyncio_detailed(
            original_image_hash=original_image_hash, client=self.api
        )
        problems.raise_for_problem(response)
        return _parsed(response)

    async def wait_for_record(self, original_image_hash: str, options: RecordWaitOptions) -> PublishedRecordResponse:
        """Poll `get_record` until its outcome is terminal; raise once `options.poll_timeout` elapses."""
        return await _poll_for_record_async(self.get_record, original_image_hash, options)

    async def get_records(self, hashes: Sequence[str]) -> PublishedRecordsResponse:
        """Recover the published records for several original image hashes (`POST /records`)."""
        body = PublishedRecordsRequestBody(original_image_hashes=list(hashes))
        response = await post_records.asyncio_detailed(client=self.api, body=body)
        problems.raise_for_problem(response)
        return _parsed(response)

    async def unregister(self, registration_id: str) -> None:
        """Take a registration down (`DELETE /registrations/{id}`)."""
        response = await delete_registrations_registration_id.asyncio_detailed(
            registration_id=uuid.UUID(registration_id), client=self.api
        )
        problems.raise_for_problem(response)

    async def account_stats(self) -> AccountStatsResponse:
        """Read the calling account's grant usage (`GET /account/stats`)."""
        response = await get_account_stats.asyncio_detailed(client=self.api)
        problems.raise_for_problem(response)
        return _parsed(response)

    async def health(self) -> HealthResponse:
        """Check the service's health (`GET /health`, anonymous)."""
        response = await get_health.asyncio_detailed(client=self.api)
        problems.raise_for_problem(response)
        return _parsed(response)

    # -- slot conversations -------------------------------------------------------------------

    async def register_batch(
        self,
        items: Sequence[RegistrationItem],
        options: RegisterBatchOptions,
        on_progress: ProgressCallback | None = None,
    ) -> RegisterBatchResult:
        """Async mirror of `ParallaxClient.register_batch`."""
        batching = _require_batching(self.options, "register_batch")

        if options.existing_slot_id is not None:
            slot_id = options.existing_slot_id
        else:
            opened = await self._with_503_retry(
                lambda: post_slots.asyncio_detailed(client=self.api), options.poll_timeout
            )
            slot_id = _parsed(opened).slot_id

        hash_to_item = slots_module.hash_registration_items(items)
        missing = await self._with_503_retry(
            lambda: post_slots_slot_id_uploads_missing.asyncio_detailed(
                slot_id=slot_id, client=self.api, body=ResumeRequestBody(hashes=list(hash_to_item.keys()))
            ),
            options.poll_timeout,
        )
        missing_hashes = _parsed(missing).missing

        outcomes = []
        for batch in slots_module.plan_registration_batches(missing_hashes, hash_to_item, batching):
            parts = multipart.build_upload_parts([(hash_to_item[h].manifests, hash_to_item[h].image) for h in batch])
            response = await self._with_503_retry(
                lambda parts=parts: self._http().post(f"/slots/{slot_id}/uploads", files=parts),
                options.poll_timeout,
            )
            outcomes.extend(SlotUploadResponse.from_dict(response.json()).outcomes)

        committed = await self._with_503_retry(
            lambda: post_slots_slot_id_commit.asyncio_detailed(slot_id=slot_id, client=self.api),
            options.poll_timeout,
        )
        commit = _parsed(committed)

        final_progress = await _poll_slot_progress_async(
            lambda: get_slots_slot_id_progress.asyncio_detailed(slot_id=slot_id, client=self.api),
            options,
            on_progress,
        )

        return RegisterBatchResult(
            slot_id=slot_id, commit=commit, final_progress=final_progress, upload_outcomes=outcomes
        )

    async def lookup_batch(
        self,
        images: Sequence[ImageUpload],
        options: LookupBatchOptions,
        on_progress: ProgressCallback | None = None,
    ) -> LookupBatchResult:
        """Async mirror of `ParallaxClient.lookup_batch`.

        A look-up commit is terminal and answers the results directly, so this call never polls
        for them: it reads `progress` once, right after commit, purely to report it, and reads
        `results` only if the commit response body came back empty. Two inputs with identical
        bytes declare and upload one hash once; the results, keyed by hash, carry that hash once.
        """
        batching = _require_batching(self.options, "lookup_batch")

        if options.existing_lookup_slot_id is not None:
            lookup_slot_id = options.existing_lookup_slot_id
        else:
            opened = await self._with_503_retry(lambda: post_lookup_slots.asyncio_detailed(client=self.api), None)
            lookup_slot_id = _parsed(opened).lookup_slot_id

        hash_to_image = slots_module.hash_images(images)
        missing = await self._with_503_retry(
            lambda: post_lookup_slots_lookup_slot_id_queries_missing.asyncio_detailed(
                lookup_slot_id=lookup_slot_id,
                client=self.api,
                body=ResumeRequestBody(hashes=list(hash_to_image.keys())),
            ),
            None,
        )
        missing_hashes = _parsed(missing).missing

        for batch in slots_module.plan_lookup_batches(missing_hashes, hash_to_image, batching):
            parts = multipart.build_lookup_parts([hash_to_image[h] for h in batch])
            await self._with_503_retry(
                lambda parts=parts: self._http().post(f"/lookup/slots/{lookup_slot_id}/queries", files=parts),
                None,
            )

        commit_response = await self._with_503_retry(
            lambda: self._http().post(f"/lookup/slots/{lookup_slot_id}/commit"), None
        )
        results = LookupResultsResponse.from_dict(commit_response.json()) if commit_response.content else None
        if results is None:
            fetched = await self._with_503_retry(
                lambda: get_lookup_slots_lookup_slot_id_results.asyncio_detailed(
                    lookup_slot_id=lookup_slot_id, client=self.api
                ),
                None,
            )
            results = _parsed(fetched)

        progress_response = await self._with_503_retry(
            lambda: get_lookup_slots_lookup_slot_id_progress.asyncio_detailed(
                lookup_slot_id=lookup_slot_id, client=self.api
            ),
            None,
        )
        final_progress = _parsed(progress_response)
        if on_progress is not None:
            on_progress(final_progress)

        return LookupBatchResult(lookup_slot_id=lookup_slot_id, results=results, final_progress=final_progress)

    # -- shared plumbing ----------------------------------------------------------------------

    async def _with_503_retry(self, call: Callable[[], Any], poll_timeout: float | None) -> Any:
        """Async mirror of `ParallaxClient._with_503_retry`."""
        response = await call()
        if 200 <= int(response.status_code) < 300:
            return response
        problem = problems.problem_from_response(response)
        wait = problems.resolve_retry_wait(problem, poll_timeout)
        if wait is None:
            raise problem
        await asyncio.sleep(wait)
        response = await call()
        if 200 <= int(response.status_code) < 300:
            return response
        raise problems.problem_from_response(response)
