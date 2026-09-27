"""Tests for the pure chain builder and sequence hash (PC-108).

Mirrors `Xio.Parallax.Common`'s `ChainRefusalTests`: one test per `PxChainRefusal`, derived from
the enum, plus the walk/reach/gap derivation and the sequence hash's own refusals.
"""

# PC-108: the chain builder and sequence hash tests

from __future__ import annotations

import random
from uuid import UUID, uuid4

import pytest
from xio_parallax_client.frames.protocol import (
    PxBodyHeader,
    PxChainBuilt,
    PxChainMember,
    PxChainRefusal,
    PxChainRefused,
    PxEndHeader,
    PxGapHeader,
    PxGapRange,
    PxHeadHeader,
)
from xio_parallax_client.frames.pure._chain import build_chain, compute_sequence_hash

SEQ: UUID = uuid4()
OTHER_SEQ: UUID = uuid4()
HASH_A = b"\x0a" * 32
HASH_B = b"\x0b" * 32
HASH_C = b"\x0c" * 32
HASH_D = b"\x0d" * 32


def _head(frame_id: int, sequence_id: UUID = SEQ) -> PxChainMember:
    return PxChainMember(PxHeadHeader(sequence_id, frame_id), HASH_A)


def _body(frame_id: int, prev: int, next_: int, sequence_id: UUID = SEQ, frame_hash: bytes = HASH_B) -> PxChainMember:
    return PxChainMember(PxBodyHeader(sequence_id, frame_id, prev, next_, 0), frame_hash)


def _end(frame_id: int, prev: int, sequence_id: UUID = SEQ) -> PxChainMember:
    return PxChainMember(PxEndHeader(sequence_id, frame_id, prev), HASH_C)


def _gap(frame_id: int, range_from: int, range_to: int) -> PxChainMember:
    return PxChainMember(PxGapHeader(SEQ, frame_id, PxGapRange(range_from, range_to)), HASH_D)


def test_head_only_reaches_head() -> None:
    """A HEAD-only member set builds a chain that reaches HEAD itself, open, unsealed, unconnected."""
    head = _head(1)
    result = build_chain([head])

    assert isinstance(result, PxChainBuilt)
    chain = result.chain
    assert chain.sequence_id == SEQ
    assert chain.walk == (head,)
    assert chain.reach == 1
    assert chain.gaps == ()
    assert chain.is_sealed is False
    assert chain.is_connected is False


def test_a_connected_chain_with_a_gap_derives_walk_reach_and_the_gap() -> None:
    """A segment beyond a gap does not extend the walk, but END still closes the tail into one gap."""
    head = _head(1)
    body2 = _body(2, prev=1, next_=3, frame_hash=HASH_B)
    body5 = _body(5, prev=4, next_=6, frame_hash=HASH_C)
    end6 = _end(6, prev=5)

    result = build_chain([end6, body5, head, body2])

    assert isinstance(result, PxChainBuilt)
    chain = result.chain
    assert [member.header.frame_id for member in chain.walk] == [1, 2]
    assert chain.reach == 2
    assert chain.gaps == (PxGapRange(3, 4),)
    assert chain.is_sealed is True
    assert chain.is_connected is False
    assert chain.body_frame_hashes_in_walk_order == (HASH_B,)


def test_members_in_any_order_build_the_same_chain() -> None:
    """A fully connected chain builds to the same result whatever order its members are given in."""
    head = _head(1)
    body2 = _body(2, prev=1, next_=3, frame_hash=HASH_B)
    body3 = _body(3, prev=2, next_=4, frame_hash=HASH_C)
    end4 = _end(4, prev=3)
    members = [head, body2, body3, end4]

    forward = build_chain(members)
    shuffled = list(members)
    random.Random(7).shuffle(shuffled)
    reordered = build_chain(shuffled)

    assert isinstance(forward, PxChainBuilt)
    assert isinstance(reordered, PxChainBuilt)
    assert forward.chain == reordered.chain
    assert forward.chain.is_connected is True
    assert forward.chain.body_frame_hashes_in_walk_order == (HASH_B, HASH_C)


def test_build_chain_refuses_an_empty_member_set() -> None:
    """An empty member set is a `ValueError`, never a refusal answer."""
    with pytest.raises(ValueError, match="at least one member"):
        build_chain([])


def test_build_chain_refuses_a_member_whose_own_links_break_its_order() -> None:
    """A BODY naming prev at or above its own id, or next at or below it, is a `ValueError` before any rule runs."""
    with pytest.raises(ValueError, match="LinkOrderInvalid"):
        build_chain([_head(1), _body(2, prev=2, next_=3)])


def test_gap_frame_not_member() -> None:
    """Rule 1: a GAP frame offered as a member is refused, GAP being an output the chain produces."""
    result = build_chain([_gap(2, 5, 6)])

    assert result == PxChainRefused(PxChainRefusal.GAP_FRAME_NOT_MEMBER, 2, result.detail)


def test_head_missing() -> None:
    """Rule 2: no member is a HEAD; the lowest member's id is named."""
    result = build_chain([_body(2, prev=1, next_=3)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.HEAD_MISSING
    assert result.frame_id == 2


def test_head_duplicated() -> None:
    """Rule 3: more than one member is a HEAD frame; the second HEAD in id order is named."""
    result = build_chain([_head(1), _head(2)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.HEAD_DUPLICATED
    assert result.frame_id == 2


def test_end_duplicated() -> None:
    """Rule 4: more than one member is an END frame; the second END in id order is named."""
    result = build_chain([_head(1), _end(2, prev=1), _end(3, prev=1)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.END_DUPLICATED
    assert result.frame_id == 3


def test_sequence_mismatch() -> None:
    """Rule 5: a member's sequence id differs from HEAD's."""
    result = build_chain([_head(1), _body(2, prev=1, next_=3, sequence_id=OTHER_SEQ)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.SEQUENCE_MISMATCH
    assert result.frame_id == 2


def test_duplicate_frame_id() -> None:
    """Rule 6: two members share one frame id."""
    result = build_chain([_head(1), _body(2, prev=1, next_=3), _body(2, prev=1, next_=4)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.DUPLICATE_FRAME_ID
    assert result.frame_id == 2


def test_below_head() -> None:
    """Rule 7: a member's id is at or below HEAD's id."""
    result = build_chain([_head(5), _body(3, prev=1, next_=4)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.BELOW_HEAD
    assert result.frame_id == 3


def test_beyond_end() -> None:
    """Rule 8: with END present, a member's id is above END's id."""
    result = build_chain([_head(1), _end(4, prev=3), _body(5, prev=1, next_=6)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.BEYOND_END
    assert result.frame_id == 5


def test_link_claimed_twice() -> None:
    """Rule 9: two members each name one id as their prev; the later claimant in id order is named."""
    result = build_chain([_head(1), _body(2, prev=1, next_=3), _body(4, prev=1, next_=5)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.LINK_CLAIMED_TWICE
    assert result.frame_id == 4


def test_link_disagreement() -> None:
    """Rule 10: a member names an arrived member as its next, which does not name it back as prev."""
    result = build_chain([_head(1), _body(2, prev=1, next_=5), _body(5, prev=3, next_=6)])

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.LINK_DISAGREEMENT
    assert result.frame_id == 2


def test_link_crossing() -> None:
    """Rule 11: two members' asserted edges overlap without being the same edge."""
    result = build_chain(
        [
            _head(1),
            _body(5, prev=1, next_=100, frame_hash=HASH_B),
            _body(50, prev=40, next_=60, frame_hash=HASH_C),
        ]
    )

    assert isinstance(result, PxChainRefused)
    assert result.reason == PxChainRefusal.LINK_CROSSING
    assert result.frame_id == 50


def test_sequence_hash_refuses_empty_and_short_hashes() -> None:
    """`compute_sequence_hash` refuses an empty list, and any hash that is not exactly 32 bytes."""
    with pytest.raises(ValueError, match="at least one BODY frame hash"):
        compute_sequence_hash([])

    with pytest.raises(ValueError, match="frame hash 1 is 10 bytes, not 32"):
        compute_sequence_hash([HASH_A, b"\x00" * 10])


def test_sequence_hash_is_blake3_of_the_concatenated_hashes_in_order() -> None:
    """The sequence hash is BLAKE3-256 of the given hashes concatenated exactly in the order given."""
    import blake3

    expected = blake3.blake3(HASH_B + HASH_C).digest()

    assert compute_sequence_hash([HASH_B, HASH_C]) == expected
    assert compute_sequence_hash([HASH_C, HASH_B]) != expected
