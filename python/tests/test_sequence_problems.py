"""PC-111: the sequences-not-enabled slug builds a typed refusal; other 403s stay plain."""

from __future__ import annotations

import httpx
import pytest
from xio_parallax_client.problems import ParallaxProblem, SequencesNotEnabled, raise_for_problem


def _response(status: int, type_: str, title: str) -> httpx.Response:
    return httpx.Response(status, json={"type": type_, "title": title, "status": status})


def test_sequences_not_enabled_slug_builds_the_typed_subclass() -> None:
    response = _response(403, "urn:xio:parallax:problem:sequences-not-enabled", "Sequences not enabled")
    with pytest.raises(SequencesNotEnabled) as excinfo:
        raise_for_problem(response)
    problem = excinfo.value
    assert problem.status == 403
    assert problem.slug == "sequences-not-enabled"
    assert isinstance(problem, ParallaxProblem)


def test_a_refused_ticket_403_stays_a_plain_parallax_problem() -> None:
    response = _response(403, "urn:xio:parallax:problem:sequence-ticket-refused", "Sequence ticket refused")
    with pytest.raises(ParallaxProblem) as excinfo:
        raise_for_problem(response)
    problem = excinfo.value
    assert not isinstance(problem, SequencesNotEnabled)
    assert problem.slug == "sequence-ticket-refused"


def test_a_bare_except_parallax_problem_still_catches_the_typed_subclass() -> None:
    response = _response(403, "urn:xio:parallax:problem:sequences-not-enabled", "Sequences not enabled")
    try:
        raise_for_problem(response)
        pytest.fail("expected a ParallaxProblem")
    except ParallaxProblem as caught:
        assert isinstance(caught, SequencesNotEnabled)


def test_status_alone_does_not_pick_the_typed_subclass() -> None:
    response = _response(403, "urn:xio:parallax:problem:some-other-refusal", "Some other refusal")
    with pytest.raises(ParallaxProblem) as excinfo:
        raise_for_problem(response)
    assert not isinstance(excinfo.value, SequencesNotEnabled)
