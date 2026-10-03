"""PC-121: the register result keeps every BODY frame's PX frame hash it encoded, in chain order.

Mirrors .NET's `RegisterSequenceFrameHashTests`: each kept hash is the trailer of the very bytes the client
uploaded for that frame, END (outside the sequence hash) is not among them, a resume keeps only the frames
it sent, and a committed sequence's resume keeps none - for the sync and the async client alike.
"""

from __future__ import annotations

import dataclasses

import pytest
import respx
from xio_parallax_client import (
    AsyncParallaxClient,
    ParallaxClientOptions,
    SequenceRegisterOptions,
    SequenceRegisterResult,
)

from .conftest import BASE_URL
from .sequence_server import SequenceConversationServer
from .test_register_sequence import (
    build_client,
    commit_response,
    register_options,
    source,
    verdict_json,
    verdict_response,
)


def _resume_options(server: SequenceConversationServer) -> SequenceRegisterOptions:
    return dataclasses.replace(register_options(max_frames_per_request=8), open=None, existing=server.opened)


def _assert_each_hash_is_its_uploaded_trailer(
    server: SequenceConversationServer, result: SequenceRegisterResult
) -> None:
    uploaded = dict(server.uploaded_frames())
    for kept in result.encoded_frame_hashes:
        assert len(kept.frame_hash) == 32
        assert kept.frame_hash == uploaded[kept.frame_id][-32:]


def _fresh_server() -> SequenceConversationServer:
    server = SequenceConversationServer(BASE_URL)
    server.sealing_frame_id = 4
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=4)
    server.commits.append(commit_response("registered", "published", "published", "published"))
    return server


@respx.mock
def test_a_fresh_register_keeps_every_body_frames_hash_in_chain_order_and_not_end() -> None:
    server = _fresh_server()

    result = build_client(server).register_sequence(source(1, 2, 3), register_options(max_frames_per_request=2))

    assert [kept.frame_id for kept in result.encoded_frame_hashes] == [1, 2, 3]
    _assert_each_hash_is_its_uploaded_trailer(server, result)


@respx.mock
@pytest.mark.asyncio
async def test_the_async_client_keeps_the_same_frame_hashes() -> None:
    server = _fresh_server()
    client = AsyncParallaxClient(ParallaxClientOptions(account_token="test-token", base_url=BASE_URL))

    result = await client.register_sequence(source(1, 2, 3), register_options(max_frames_per_request=2))

    assert [kept.frame_id for kept in result.encoded_frame_hashes] == [1, 2, 3]
    _assert_each_hash_is_its_uploaded_trailer(server, result)


@respx.mock
def test_resuming_an_open_sequence_keeps_only_the_frames_this_run_sent() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("open", connected=False, reach=3))
    server.sealing_frame_id = 7
    server.sealing_verdict_json = verdict_json("sealed", connected=True, reach=7)
    server.commits.append(commit_response("registered", "published"))

    result = build_client(server).register_sequence(source(1, 2, 3, 4, 5, 6), _resume_options(server))

    assert [kept.frame_id for kept in result.encoded_frame_hashes] == [4, 5, 6]
    _assert_each_hash_is_its_uploaded_trailer(server, result)


@respx.mock
def test_resuming_a_committed_sequence_keeps_no_frame_hash() -> None:
    server = SequenceConversationServer(BASE_URL)
    server.progress.append(verdict_response("committed", connected=True, reach=7))
    server.commits.append(commit_response("alreadyRegistered", "alreadyPublished"))

    result = build_client(server).register_sequence(source(1, 2, 3), _resume_options(server))

    assert result.encoded_frame_hashes == ()
