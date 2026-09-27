"""The seven generated-builder sequence routes on `ParallaxClient`: gaps, progress, amend, commit,
results and abandon, mirroring `ParallaxClientSequencesRouteTests`. Open and the frames routes,
sent through the hand-written multipart sender, are in `test_sequence_routes.py`.
"""

# PC-113: rework - story key at the change site; the seven generated-builder route tests

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest
import respx
from xio_parallax_client import ParallaxClient, ParallaxClientOptions, ParallaxProblem
from xio_parallax_client.sequences import SequenceHandle
from xio_parallax_client.sequences.wire import TICKET_HEADER

from .conftest import BASE_URL


@respx.mock
def test_get_sequence_gaps_sends_get_gaps_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-gaps")
    route = respx.get(f"{BASE_URL}/sequences/{handle.sequence_id}/gaps").mock(
        return_value=httpx.Response(200, json={"gaps": [{"from": 2, "to": 4, "gapFrame": "AAA="}]})
    )
    client = ParallaxClient(options)

    response = client.get_sequence_gaps(handle)

    assert len(response.gaps) == 1
    assert response.gaps[0].from_ == 2
    assert response.gaps[0].to == 4
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-gaps"


@respx.mock
def test_get_sequence_progress_sends_get_progress_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-progress")
    route = respx.get(f"{BASE_URL}/sequences/{handle.sequence_id}/progress").mock(
        return_value=httpx.Response(
            200,
            json={
                "state": "open",
                "framesReceived": 3,
                "expectedSize": None,
                "reach": 3,
                "connected": False,
                "gaps": [],
                "errata": [],
            },
        )
    )
    client = ParallaxClient(options)

    response = client.get_sequence_progress(handle)

    assert response.state == "open"
    assert response.frames_received == 3
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-progress"


@respx.mock
def test_amend_sequence_expected_size_sends_put_expected_size_under_the_ticket_header(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-amend")
    route = respx.put(f"{BASE_URL}/sequences/{handle.sequence_id}/expected-size").mock(
        return_value=httpx.Response(204)
    )
    client = ParallaxClient(options)

    assert client.amend_sequence_expected_size(handle, 99) is None

    request = route.calls.last.request
    assert json.loads(request.content)["expectedSize"] == 99
    assert request.headers[TICKET_HEADER] == "sequence-ticket-amend"


@pytest.mark.parametrize("expected_size", [0, -1, 2**31])
def test_amend_sequence_expected_size_refuses_out_of_range_before_sending_any_request(
    options: ParallaxClientOptions, expected_size: int
) -> None:
    handle = SequenceHandle(uuid4(), "t")
    client = ParallaxClient(options)

    with respx.mock:
        route = respx.put(f"{BASE_URL}/sequences/{handle.sequence_id}/expected-size").mock(
            return_value=httpx.Response(204)
        )
        with pytest.raises(ValueError, match="expected_size"):
            client.amend_sequence_expected_size(handle, expected_size)
        assert route.call_count == 0


@respx.mock
def test_commit_sequence_sends_post_commit_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-commit")
    route = respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/commit").mock(
        return_value=httpx.Response(
            200,
            json={"outcome": "registered", "sequenceHash": "abc123", "sequenceRecordPublished": True, "frames": []},
        )
    )
    client = ParallaxClient(options)

    response = client.commit_sequence(handle)

    assert response.outcome == "registered"
    assert response.sequence_hash == "abc123"
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-commit"


@respx.mock
def test_commit_sequence_when_the_sequence_has_shortfalls_raises_the_typed_problem(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-commit-409")
    respx.post(f"{BASE_URL}/sequences/{handle.sequence_id}/commit").mock(
        return_value=httpx.Response(
            409, json={"type": "urn:xio:parallax:problem:sequence-not-committable", "title": "Not committable"}
        )
    )
    client = ParallaxClient(options)

    with pytest.raises(ParallaxProblem) as excinfo:
        client.commit_sequence(handle)
    assert excinfo.value.status == 409
    assert excinfo.value.slug == "sequence-not-committable"


@respx.mock
def test_get_sequence_results_sends_get_results_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-results")
    route = respx.get(f"{BASE_URL}/sequences/{handle.sequence_id}/results").mock(
        return_value=httpx.Response(
            200,
            json={
                "sequenceHash": "def456",
                "outcome": "alreadyRegistered",
                "finalSize": 10,
                "committedAt": "2026-09-26T00:00:00Z",
            },
        )
    )
    client = ParallaxClient(options)

    response = client.get_sequence_results(handle)

    assert response.outcome == "alreadyRegistered"
    assert response.final_size == 10
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-results"


@respx.mock
def test_abandon_sequence_sends_delete_sequence_under_the_ticket_header_and_maps_the_response(
    options: ParallaxClientOptions,
) -> None:
    handle = SequenceHandle(uuid4(), "sequence-ticket-abandon")
    route = respx.delete(f"{BASE_URL}/sequences/{handle.sequence_id}").mock(
        return_value=httpx.Response(
            200, json={"sequenceId": str(handle.sequence_id), "state": "abandoned", "packetsPurged": 4}
        )
    )
    client = ParallaxClient(options)

    response = client.abandon_sequence(handle)

    assert response.state == "abandoned"
    assert response.packets_purged == 4
    assert route.calls.last.request.headers[TICKET_HEADER] == "sequence-ticket-abandon"
