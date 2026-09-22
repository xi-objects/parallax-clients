"""Typed problem parsing: status, slug, extensions, and the 503-only `Retry-After`."""

from __future__ import annotations

import httpx
import pytest
from xio_parallax_client import ParallaxProblem
from xio_parallax_client.problems import raise_for_problem, resolve_retry_wait


def _response(status: int, body: dict | None, headers: dict[str, str] | None = None) -> httpx.Response:
    kwargs: dict = {"headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return httpx.Response(status, **kwargs)


def test_raise_for_problem_is_a_noop_on_2xx() -> None:
    raise_for_problem(_response(200, {"ok": True}))
    raise_for_problem(_response(204, None))


def test_raise_for_problem_parses_the_documented_extensions() -> None:
    body = {
        "type": "urn:xio:parallax:problem:registration-grant-exhausted",
        "title": "Registration grant exhausted",
        "status": 429,
        "detail": "No registrations remain on this account's grant.",
        "traceId": "trace-abc-123",
        "cap": "MaxRegistrationsPerAccount",
        "registrationId": "22222222-2222-2222-2222-222222222222",
        "registrationRemaining": "0",
        "lookupRemaining": 5,
    }
    with pytest.raises(ParallaxProblem) as excinfo:
        raise_for_problem(_response(429, body))

    problem = excinfo.value
    assert problem.status == 429
    assert problem.type == "urn:xio:parallax:problem:registration-grant-exhausted"
    assert problem.slug == "registration-grant-exhausted"
    assert problem.title == "Registration grant exhausted"
    assert problem.detail == "No registrations remain on this account's grant."
    assert problem.trace_id == "trace-abc-123"
    assert problem.cap == "MaxRegistrationsPerAccount"
    assert problem.registration_id == "22222222-2222-2222-2222-222222222222"
    assert problem.registration_remaining == 0
    assert isinstance(problem.registration_remaining, int)
    assert problem.lookup_remaining == 5
    assert problem.retry_after is None


def test_raise_for_problem_reads_retry_after_only_when_present() -> None:
    body = {
        "type": "urn:xio:parallax:problem:image-not-checked-yet",
        "title": "Image could not be checked yet",
        "status": 503,
    }
    with pytest.raises(ParallaxProblem) as excinfo:
        raise_for_problem(_response(503, body, headers={"Retry-After": "2.5"}))

    problem = excinfo.value
    assert problem.status == 503
    assert problem.slug == "image-not-checked-yet"
    assert problem.retry_after == pytest.approx(2.5)


def test_raise_for_problem_handles_a_non_problem_body() -> None:
    response = httpx.Response(500, content=b"not json at all")
    with pytest.raises(ParallaxProblem) as excinfo:
        raise_for_problem(response)

    problem = excinfo.value
    assert problem.status == 500
    assert problem.type is None
    assert problem.slug is None
    assert problem.title is None


def test_resolve_retry_wait_only_for_503_with_retry_after() -> None:
    retryable = ParallaxProblem(
        status=503,
        type="urn:xio:parallax:problem:image-not-checked-yet",
        slug="image-not-checked-yet",
        title=None,
        detail=None,
        trace_id=None,
        cap=None,
        registration_id=None,
        registration_remaining=None,
        lookup_remaining=None,
        retry_after=10.0,
    )
    assert resolve_retry_wait(retryable, cap=3.0) == 3.0
    assert resolve_retry_wait(retryable, cap=30.0) == 10.0

    no_header = ParallaxProblem(
        status=503,
        type=None,
        slug=None,
        title=None,
        detail=None,
        trace_id=None,
        cap=None,
        registration_id=None,
        registration_remaining=None,
        lookup_remaining=None,
        retry_after=None,
    )
    assert resolve_retry_wait(no_header, cap=30.0) is None

    other_status = ParallaxProblem(
        status=409,
        type=None,
        slug=None,
        title=None,
        detail=None,
        trace_id=None,
        cap=None,
        registration_id=None,
        registration_remaining=None,
        lookup_remaining=None,
        retry_after=5.0,
    )
    assert resolve_retry_wait(other_status, cap=30.0) is None
