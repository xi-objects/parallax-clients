"""The chain rules 1-11, checked in order over a member set sorted by frame id.

Mirrors `Xio.Parallax.Common`'s `PxChainRules` (`docs/px-frame.md`, "The chain"): rule declaration
order is check order, and each rule is checked over every member before the next rule runs.
"""

# PC-108: the chain rules 1-11, in the format's declaration order

from __future__ import annotations

from dataclasses import dataclass

from xio_parallax_client.frames.protocol import (
    PxBodyHeader,
    PxChainMember,
    PxChainRefusal,
    PxChainRefused,
    PxEndHeader,
    PxFrameRefusal,
    PxFrameType,
    PxGapHeader,
    PxHeadHeader,
)


@dataclass(frozen=True, slots=True)
class ChainNode:
    """PC-108: a member with its frame type and links read once from its header; None is a link the type lacks."""

    member: PxChainMember
    frame_type: PxFrameType
    frame_id: int
    prev: int | None
    next: int | None


@dataclass(frozen=True, slots=True)
class ChainEdge:
    """PC-108: an edge a member asserts, the open interval (from, to)."""

    edge_from: int
    edge_to: int
    owner_frame_id: int


def to_node(member: PxChainMember) -> ChainNode:
    """PC-108: a member's type and links, raising ValueError for links that break its own frame type's order."""
    header = member.header
    if isinstance(header, PxHeadHeader):
        node = ChainNode(member, PxFrameType.HEAD, header.frame_id, None, None)
    elif isinstance(header, PxBodyHeader):
        node = ChainNode(member, PxFrameType.BODY, header.frame_id, header.prev, header.next)
    elif isinstance(header, PxEndHeader):
        node = ChainNode(member, PxFrameType.END, header.frame_id, header.prev, None)
    elif isinstance(header, PxGapHeader):
        node = ChainNode(member, PxFrameType.GAP, header.frame_id, None, None)
    else:
        raise ValueError(f"{type(header).__name__} is no frame type")  # noqa: TRY004 (build_chain raises ValueError only)

    if node.prev is not None and node.prev >= node.frame_id:
        detail = f"frame {node.frame_id} names prev {node.prev} and next {node.next} out of order"
        raise ValueError(f"{PxFrameRefusal.LINK_ORDER_INVALID.value}: {detail}")
    if node.next is not None and node.next <= node.frame_id:
        detail = f"frame {node.frame_id} names prev {node.prev} and next {node.next} out of order"
        raise ValueError(f"{PxFrameRefusal.LINK_ORDER_INVALID.value}: {detail}")
    return node


def check_rules(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rules 1-11 in order over nodes sorted by frame id; None when none is broken."""
    type_refusal = _check_gap_members(nodes) or _check_head_and_end_counts(nodes)
    if type_refusal is not None:
        return type_refusal

    head = next(node for node in nodes if node.frame_type == PxFrameType.HEAD)
    end = next((node for node in nodes if node.frame_type == PxFrameType.END), None)

    return (
        _check_sequence(nodes, head)
        or _check_duplicate_frame_ids(nodes)
        or _check_below_head(nodes, head)
        or _check_beyond_end(nodes, end)
        or _check_links_claimed_twice(nodes)
        or _check_link_agreement(nodes)
        or _check_link_crossing(nodes)
    )


def _check_gap_members(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rule 1, a GAP is an output of the chain, never a member."""
    for node in nodes:
        if node.frame_type == PxFrameType.GAP:
            detail = f"frame {node.frame_id} is a GAP, which a chain produces and never takes"
            return PxChainRefused(PxChainRefusal.GAP_FRAME_NOT_MEMBER, node.frame_id, detail)
    return None


def _check_head_and_end_counts(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rules 2-4, exactly one HEAD and at most one END; a missing HEAD names the lowest member."""
    heads = [node for node in nodes if node.frame_type == PxFrameType.HEAD]
    ends = [node for node in nodes if node.frame_type == PxFrameType.END]
    if not heads:
        detail = f"no member is a HEAD; the lowest member is frame {nodes[0].frame_id}"
        return PxChainRefused(PxChainRefusal.HEAD_MISSING, nodes[0].frame_id, detail)
    if len(heads) > 1:
        detail = f"frames {heads[0].frame_id} and {heads[1].frame_id} are both HEAD"
        return PxChainRefused(PxChainRefusal.HEAD_DUPLICATED, heads[1].frame_id, detail)
    if len(ends) > 1:
        detail = f"frames {ends[0].frame_id} and {ends[1].frame_id} are both END"
        return PxChainRefused(PxChainRefusal.END_DUPLICATED, ends[1].frame_id, detail)
    return None


def _check_sequence(nodes: list[ChainNode], head: ChainNode) -> PxChainRefused | None:
    """PC-108: rule 5, every member carries HEAD's sequence id."""
    sequence_id = head.member.header.sequence_id
    for node in nodes:
        if node.member.header.sequence_id != sequence_id:
            detail = f"frame {node.frame_id} is in sequence {node.member.header.sequence_id}, not HEAD's {sequence_id}"
            return PxChainRefused(PxChainRefusal.SEQUENCE_MISMATCH, node.frame_id, detail)
    return None


def _check_duplicate_frame_ids(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rule 6, no two members share a frame id; sorted, a repeat is adjacent."""
    for index in range(1, len(nodes)):
        if nodes[index].frame_id == nodes[index - 1].frame_id:
            detail = f"two members share frame id {nodes[index].frame_id}"
            return PxChainRefused(PxChainRefusal.DUPLICATE_FRAME_ID, nodes[index].frame_id, detail)
    return None


def _check_below_head(nodes: list[ChainNode], head: ChainNode) -> PxChainRefused | None:
    """PC-108: rule 7, every other member's id is above HEAD's and no prev is below it."""
    for node in nodes:
        if node is head:
            continue
        if node.frame_id <= head.frame_id:
            detail = f"frame {node.frame_id} is at or below HEAD {head.frame_id}"
            return PxChainRefused(PxChainRefusal.BELOW_HEAD, node.frame_id, detail)
        if node.prev is not None and node.prev < head.frame_id:
            detail = f"frame {node.frame_id} names prev {node.prev}, below HEAD {head.frame_id}"
            return PxChainRefused(PxChainRefusal.BELOW_HEAD, node.frame_id, detail)
    return None


def _check_beyond_end(nodes: list[ChainNode], end: ChainNode | None) -> PxChainRefused | None:
    """PC-108: rule 8, with END present no other member's id and no next is above END's id."""
    if end is None:
        return None
    for node in nodes:
        if node is end:
            continue
        if node.frame_id > end.frame_id:
            detail = f"frame {node.frame_id} is above END {end.frame_id}"
            return PxChainRefused(PxChainRefusal.BEYOND_END, node.frame_id, detail)
        if node.next is not None and node.next > end.frame_id:
            detail = f"frame {node.frame_id} names next {node.next}, above END {end.frame_id}"
            return PxChainRefused(PxChainRefusal.BEYOND_END, node.frame_id, detail)
    return None


def _check_links_claimed_twice(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rule 9, no id is named as prev by two members, nor as next by two; the later claimant is named."""
    prev_claims: dict[int, int] = {}
    next_claims: dict[int, int] = {}
    for node in nodes:
        if node.prev is not None:
            if node.prev in prev_claims:
                detail = f"frames {prev_claims[node.prev]} and {node.frame_id} both name {node.prev} as prev"
                return PxChainRefused(PxChainRefusal.LINK_CLAIMED_TWICE, node.frame_id, detail)
            prev_claims[node.prev] = node.frame_id
        if node.next is not None:
            if node.next in next_claims:
                detail = f"frames {next_claims[node.next]} and {node.frame_id} both name {node.next} as next"
                return PxChainRefused(PxChainRefusal.LINK_CLAIMED_TWICE, node.frame_id, detail)
            next_claims[node.next] = node.frame_id
    return None


def _check_link_agreement(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rule 10, an arrived next names this member back as prev, and an arrived BODY prev names it back."""
    by_frame_id = {node.frame_id: node for node in nodes}
    for node in nodes:
        if node.next is not None:
            successor = by_frame_id.get(node.next)
            if successor is not None and successor.prev != node.frame_id:
                detail = f"frame {node.frame_id} names {node.next} as next, which names {successor.prev} as prev"
                return PxChainRefused(PxChainRefusal.LINK_DISAGREEMENT, node.frame_id, detail)
        if node.prev is not None:
            predecessor = by_frame_id.get(node.prev)
            if predecessor is not None and predecessor.frame_type == PxFrameType.BODY and predecessor.next != node.frame_id:
                detail = f"frame {node.frame_id} names {node.prev} as prev, which names {predecessor.next} as next"
                return PxChainRefused(PxChainRefusal.LINK_DISAGREEMENT, node.frame_id, detail)
    return None


def _check_link_crossing(nodes: list[ChainNode]) -> PxChainRefused | None:
    """PC-108: rule 11, edges sorted by their ends overlap only as the one agreed edge."""
    edges: list[ChainEdge] = []
    for node in nodes:
        if node.prev is not None:
            edges.append(ChainEdge(node.prev, node.frame_id, node.frame_id))
        if node.next is not None:
            edges.append(ChainEdge(node.frame_id, node.next, node.frame_id))

    edges.sort(key=lambda edge: (edge.edge_from, edge.edge_to, edge.owner_frame_id))

    widest: ChainEdge | None = None
    for index, edge in enumerate(edges):
        if index > 0 and edge.edge_from == edges[index - 1].edge_from and edge.edge_to == edges[index - 1].edge_to:
            continue
        if widest is not None and edge.edge_from < widest.edge_to:
            detail = (
                f"edge ({edge.edge_from}, {edge.edge_to}) of frame {edge.owner_frame_id} crosses "
                f"edge ({widest.edge_from}, {widest.edge_to}) of frame {widest.owner_frame_id}"
            )
            return PxChainRefused(PxChainRefusal.LINK_CROSSING, edge.owner_frame_id, detail)
        widest = edge if widest is None or edge.edge_to > widest.edge_to else widest
    return None
