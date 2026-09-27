"""Resuming the register conversation from each state the sequence's progress answers.

Mirrors `RegisterSequenceResumeTests` (.NET). Reuses `test_register_sequence`'s `source`,
`build_client`, `verdict_response`/`verdict_json` and `commit_response`.
"""

# PC-114: resuming the register conversation, sync

from __future__ import annotations

import dataclasses

import pytest
import respx
from xio_parallax_client import ParallaxClientError, SequenceRegisterOptions

from .conftest import BASE_URL
from .sequence_server import SequenceConversationServer
from .test_register_sequence import (
    build_client,
    commit_response,
    frames_requests,
    register_options,
    source,
    verdict_json,
    verdict_response,
)


def _resume_options(server: SequenceConversationServer) -> SequenceRegisterOptions:
    """`register_options` for a resume: no `open`, `existing` the server's own opened sequence."""
    fresh = register_options(max_frames_per_request=8)
    return dataclasses.replace(fresh, open=None, existing=server.opened)


@respx.mock
def test_resuming_an_open_sequence_uploads_only_the_frames_in_a_gap_or_above_the_reach_then_end() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("open", connected=False, reach=3))
    server.gaps_json = '{"gaps": [{"from": 4, "to": 4, "gapFrame": "AAA="}]}'
    server.sealing_frame_id = 7
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=7)
    server.commits.append(commit_response("registered", "published"))
    client = build_client(server)
    reports: list[object] = []

    result = client.register_sequence(source(1, 2, 3, 4, 5, 6), _resume_options(server), reports.append)

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [
        f"GET {prefix}/progress",
        f"GET {prefix}/gaps",
        f"POST {prefix}/frames",
        f"POST {prefix}/frames",
        f"POST {prefix}/commit",
        f"GET {prefix}/results",
    ]
    assert server.uploaded_frame_ids() == [[4, 5, 6], [7]]
    batches = server.decode_uploads()
    first = batches[0][0]
    assert (first.frame_type.name, first.frame_id, first.prev, first.next) == ("BODY", 4, 3, 5)
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in batches[1]] == [("END", 7, 6, None)]
    assert result.sequence == server.opened
    assert len(reports) == 2


@respx.mock
def test_resuming_a_sealed_sequence_uploads_only_the_gap_fills_and_no_end() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("sealed", connected=False, reach=3, gaps='[{"from": 4, "to": 4}]'))
    server.progress.append(verdict_response("sealed", connected=True, reach=7))
    server.gaps_json = '{"gaps": [{"from": 4, "to": 4, "gapFrame": "AAA="}]}'
    server.commits.append(commit_response("registered", "published"))
    client = build_client(server)

    result = client.register_sequence(source(1, 2, 3, 4, 5, 6), _resume_options(server))

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [
        f"GET {prefix}/progress",
        f"GET {prefix}/gaps",
        f"POST {prefix}/frames",
        f"GET {prefix}/progress",
        f"POST {prefix}/commit",
        f"GET {prefix}/results",
    ]
    batches = server.decode_uploads()
    assert len(batches) == 1
    only = batches[0]
    assert [(f.frame_type.name, f.frame_id, f.prev, f.next) for f in only] == [("BODY", 4, 3, 5)]
    assert result.verdict.connected is True


@respx.mock
def test_resuming_a_committed_sequence_sends_only_commit_and_results() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("committed", connected=True, reach=7))
    server.commits.append(commit_response("alreadyRegistered", "alreadyPublished"))
    client = build_client(server)

    result = client.register_sequence(source(1, 2, 3), _resume_options(server))

    prefix = f"/sequences/{server.sequence_id}"
    assert server.calls == [f"GET {prefix}/progress", f"POST {prefix}/commit", f"GET {prefix}/results"]
    assert result.commit.outcome == "alreadyRegistered"
    assert result.verdict.state == "committed"
    assert frames_requests(server) == []


@respx.mock
def test_resuming_an_abandoned_sequence_raises_naming_the_state() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("abandoned", connected=False, reach=2))
    client = build_client(server)

    with pytest.raises(ParallaxClientError) as excinfo:
        client.register_sequence(source(1, 2, 3), _resume_options(server))

    assert "abandoned" in str(excinfo.value)
    assert server.calls == [f"GET /sequences/{server.sequence_id}/progress"]
