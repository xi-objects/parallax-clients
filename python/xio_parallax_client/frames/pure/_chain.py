"""Builds a PX chain from a member set, and computes the sequence hash over BODY frame hashes.

Mirrors `Xio.Parallax.Common`'s `PxChainBuilder` and `PxSequenceHasher` (`docs/px-frame.md`, "The
chain", "Gaps and the reach", "The sequence hash"): sort by id, check the chain rules in order,
then derive the walk, reach, gaps, sealed and connected from the sorted, checked members.
"""

# PC-108: build_chain and compute_sequence_hash, the two members _chain_rules.py backs

from __future__ import annotations

from collections.abc import Collection, Sequence

import blake3

from xio_parallax_client.frames.protocol import (
    PxChain,
    PxChainBuildResult,
    PxChainBuilt,
    PxChainMember,
    PxFrameType,
    PxGapRange,
)

from ._chain_rules import ChainNode, check_rules, to_node

_HASH_LENGTH = 32


def build_chain(members: Collection[PxChainMember]) -> PxChainBuildResult:
    """PC-108: sort members by id, check the chain rules, then derive the chain; mirrors `PxChainBuilder.Build`."""
    if len(members) == 0:
        raise ValueError("a chain needs at least one member")

    nodes = [to_node(member) for member in members]
    nodes.sort(key=_sort_key)

    refused = check_rules(nodes)
    if refused is not None:
        return refused
    return PxChainBuilt(_derive(nodes))


def compute_sequence_hash(body_frame_hashes: Sequence[bytes]) -> bytes:
    """PC-108: BLAKE3-256 over the given hashes concatenated in order; mirrors `PxSequenceHasher.ComputeAsync`."""
    if len(body_frame_hashes) == 0:
        raise ValueError("a sequence hash needs at least one BODY frame hash")

    preimage = bytearray(len(body_frame_hashes) * _HASH_LENGTH)
    for index, frame_hash in enumerate(body_frame_hashes):
        if len(frame_hash) != _HASH_LENGTH:
            raise ValueError(f"frame hash {index} is {len(frame_hash)} bytes, not {_HASH_LENGTH}")
        preimage[index * _HASH_LENGTH : (index + 1) * _HASH_LENGTH] = frame_hash

    return blake3.blake3(bytes(preimage)).digest()


def _sort_key(node: ChainNode) -> tuple[int, int, str]:
    """PC-108: frame id, then frame type, then sequence id, so every input order sorts alike."""
    return (node.frame_id, int(node.frame_type), str(node.member.header.sequence_id))


def _derive(nodes: list[ChainNode]) -> PxChain:
    """PC-108: the walk from HEAD, its reach, the gaps between segments, sealed and connected."""
    head = nodes[0]
    by_frame_id = {node.frame_id: node for node in nodes}
    after_head = next((node for node in nodes if node.prev == head.frame_id), None)

    walk = [head.member]
    last = head
    successor = after_head
    while successor is not None:
        walk.append(successor.member)
        last = successor
        successor = by_frame_id.get(successor.next) if successor.next is not None else None

    gaps: list[PxGapRange] = []
    for index in range(1, len(nodes)):
        lower = nodes[index - 1]
        upper = nodes[index]
        lower_is_head = lower.frame_type == PxFrameType.HEAD
        linked = upper.prev == head.frame_id if lower_is_head else lower.next == upper.frame_id
        if not linked:
            gap_from = head.frame_id + 1 if lower_is_head else lower.next
            gaps.append(PxGapRange(gap_from, upper.prev))

    is_sealed = nodes[-1].frame_type == PxFrameType.END
    is_connected = last.frame_type == PxFrameType.END
    return PxChain(head.member.header.sequence_id, tuple(walk), last.frame_id, tuple(gaps), is_sealed, is_connected)
