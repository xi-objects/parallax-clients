"""Typed refusals: every non-2xx response from a hand-written call becomes a `ParallaxProblem`."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


class ParallaxClientError(Exception):
    """A client-side refusal the server never saw: a missing required option, or a timed-out poll."""


class ParallaxProblem(Exception):
    """One non-2xx response from the XI Parallax REST API.

    Typed from its `application/problem+json` body (`ProblemDetails`): `type` is a URN
    `urn:xio:parallax:problem:<slug>`, whose trailing segment is exposed as `slug`; `cap`,
    `registration_id`, `registration_remaining` and `lookup_remaining` are the document's problem
    extensions; `retry_after` is the `Retry-After` header, in seconds, sent only on the 503
    "image could not be checked yet". A body that is not a problem document still raises this,
    with whatever is known left `None`.
    """

    def __init__(
        self,
        *,
        status: int,
        type: str | None,
        slug: str | None,
        title: str | None,
        detail: str | None,
        trace_id: str | None,
        cap: str | None,
        registration_id: str | None,
        registration_remaining: int | None,
        lookup_remaining: int | None,
        retry_after: float | None,
    ) -> None:
        message = title or type or f"XI Parallax API refused with status {status}"
        super().__init__(f"{status}: {message}")
        self.status = status
        self.type = type
        self.slug = slug
        self.title = title
        self.detail = detail
        self.trace_id = trace_id
        self.cap = cap
        self.registration_id = registration_id
        self.registration_remaining = registration_remaining
        self.lookup_remaining = lookup_remaining
        self.retry_after = retry_after


# PC-111: the typed 403 a sequence route answers when the account has no Sequences access
class SequencesNotEnabled(ParallaxProblem):
    """The 403 the server answers on any `/sequences` route when the account lacks Sequences access.

    Matched by the problem slug `sequences-not-enabled`, not by status alone: a refused ticket is
    also a 403 (`sequence-ticket-refused`) and stays a plain `ParallaxProblem`.
    """


# PC-111: slug to typed-subclass mapping, the one place a problem slug gets its own exception type
_TYPED_PROBLEMS: dict[str, type[ParallaxProblem]] = {
    "sequences-not-enabled": SequencesNotEnabled,
}


@runtime_checkable
class _ProblemResponse(Protocol):
    """The minimal response shape `problems.py` needs: both httpx's own `Response` and the
    generated client's `Response[T]` wrapper satisfy it."""

    status_code: int
    content: bytes
    headers: Mapping[str, str]


def _slug_from_type(type_: str | None) -> str | None:
    """Return the trailing segment of a `urn:xio:parallax:problem:<slug>` URN, or `None`."""
    if not type_:
        return None
    return type_.rsplit(":", 1)[-1]


def _as_int(value: Any) -> int | None:
    """Normalize the document's `int | string` unions to a plain `int`, or `None`."""
    if value is None:
        return None
    return int(value)


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """Parse the `Retry-After` header as seconds, when present and numeric."""
    value = headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def problem_from_response(response: _ProblemResponse) -> ParallaxProblem:
    """Build a `ParallaxProblem` from a non-2xx response, whether or not its body is a problem document."""
    status = int(response.status_code)
    body: dict[str, Any] = {}
    content = response.content
    if content:
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            body = parsed
    type_ = body.get("type")
    slug = _slug_from_type(type_)
    # PC-111: the slug, not the status, picks the typed subclass; a plain ParallaxProblem otherwise
    problem_type = _TYPED_PROBLEMS.get(slug, ParallaxProblem)
    return problem_type(
        status=status,
        type=type_,
        slug=slug,
        title=body.get("title"),
        detail=body.get("detail"),
        trace_id=body.get("traceId"),
        cap=body.get("cap"),
        registration_id=body.get("registrationId"),
        registration_remaining=_as_int(body.get("registrationRemaining")),
        lookup_remaining=_as_int(body.get("lookupRemaining")),
        retry_after=_retry_after_seconds(response.headers),
    )


def raise_for_problem(response: _ProblemResponse) -> None:
    """Raise `ParallaxProblem` if `response` is not a 2xx; do nothing otherwise."""
    if 200 <= int(response.status_code) < 300:
        return
    raise problem_from_response(response)


def resolve_retry_wait(problem: ParallaxProblem, cap: float | None = None) -> float | None:
    """Return the wait, in seconds, to retry once after a 503 with `Retry-After`, capped at `cap`
    when one is given.

    Returns `None` for any problem that is not that one retryable case, since nothing else is
    retried silently.
    """
    if problem.status == 503 and problem.retry_after is not None:
        return problem.retry_after if cap is None else min(problem.retry_after, cap)
    return None
