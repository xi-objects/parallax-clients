"""The JUMBF (ISO/IEC 19566-5) box grammar, enough to walk a manifest store without parsing its CBOR.

The walk decides only well-formedness (box headers, lengths within their container, a `jumb` opening
with a `jumd`, bounded nesting); REST validates JUMBF itself. The C2PA manifest-store UUID and label
classify a well-formed store as kind `c2pa`; any other well-formed store is kind `jumbf`. Neither refuses.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .models import JumbfBoxSummary

#: The UUID a C2PA manifest store's description box carries.
C2PA_STORE_UUID = bytes.fromhex("6332706100110010800000AA00389B71")
#: The label a C2PA manifest store's description box carries.
C2PA_STORE_LABEL = "c2pa"
#: The manifest kind of a store whose description carries the C2PA manifest-store UUID and label.
C2PA_KIND = "c2pa"
#: The manifest kind of any other well-formed JUMBF store.
JUMBF_KIND = "jumbf"

_LABEL_TOGGLE = 0x02
_UUID_LENGTH = 16
_MAX_DEPTH = 64


class JumbfError(ValueError):
    """The bytes are not well-formed JUMBF; the message says where and why."""


@dataclass(frozen=True, slots=True)
class BoxHeader:
    """One box's position: its type, where its payload starts, and where the box ends."""

    type: str
    payload_start: int
    end: int


@dataclass(frozen=True, slots=True)
class Description:
    """The fields of a `jumd` description box that identify a superbox."""

    uuid: bytes
    label: str | None


def read_box_header(data: bytes, offset: int, limit: int) -> BoxHeader:
    """Read the LBox/TBox (and XLBox) header at `offset`; the box must end at or before `limit`."""
    if limit - offset < 8:
        raise JumbfError(f"box header at offset {offset} is truncated")
    lbox, tbox = struct.unpack_from(">I4s", data, offset)
    box_type = tbox.decode("latin-1")
    header_length = 8
    if lbox == 1:
        if limit - offset < 16:
            raise JumbfError(f"box {box_type!r} at offset {offset} declares an XLBox but is truncated")
        (lbox,) = struct.unpack_from(">Q", data, offset + 8)
        header_length = 16
    elif lbox == 0:
        lbox = limit - offset
    if lbox < header_length or offset + lbox > limit:
        raise JumbfError(f"box {box_type!r} at offset {offset} declares length {lbox}, outside its container")
    return BoxHeader(type=box_type, payload_start=offset + header_length, end=offset + lbox)


def parse_description(data: bytes, start: int, end: int) -> Description:
    """Parse a `jumd` payload: UUID, toggles, then the optional NUL-terminated label (invalid UTF-8 is replaced)."""
    if end - start < _UUID_LENGTH + 1:
        raise JumbfError(f"jumd box at offset {start} is shorter than its UUID and toggles")
    uuid = data[start : start + _UUID_LENGTH]
    toggles = data[start + _UUID_LENGTH]
    label: str | None = None
    if toggles & _LABEL_TOGGLE:
        label_start = start + _UUID_LENGTH + 1
        terminator = data.find(b"\x00", label_start, end)
        if terminator < 0:
            raise JumbfError(f"jumd box at offset {start} declares a label with no NUL terminator")
        label = data[label_start:terminator].decode("utf-8", errors="replace")
    return Description(uuid=uuid, label=label)


def _walk(data: bytes, start: int, end: int, depth: int, out: list[JumbfBoxSummary]) -> None:
    """Append a summary of every box in `data[start:end]`, descending into `jumb` superboxes."""
    if depth > _MAX_DEPTH:
        raise JumbfError(f"JUMBF nesting exceeds {_MAX_DEPTH} levels")
    offset = start
    while offset < end:
        header = read_box_header(data, offset, end)
        if header.type != "jumb":
            label = None
            if header.type == "jumd":
                label = parse_description(data, header.payload_start, header.end).label
            out.append(JumbfBoxSummary(type=header.type, label=label, depth=depth, length=header.end - offset))
            offset = header.end
            continue
        description = _first_description(data, header)
        out.append(JumbfBoxSummary(type="jumb", label=description.label, depth=depth, length=header.end - offset))
        _walk(data, header.payload_start, header.end, depth + 1, out)
        offset = header.end


def _first_description(data: bytes, superbox: BoxHeader) -> Description:
    """Return the description of a `jumb` superbox, whose first child must be a `jumd` box."""
    child = read_box_header(data, superbox.payload_start, superbox.end)
    if child.type != "jumd":
        raise JumbfError(f"jumb box's first child is {child.type!r}, not a jumd description box")
    return parse_description(data, child.payload_start, child.end)


def _superbox_header(data: bytes) -> BoxHeader:
    """The header of the box `data` opens with, which must be a `jumb` superbox."""
    header = read_box_header(data, 0, len(data))
    if header.type != "jumb":
        raise JumbfError(f"the data is a {header.type!r} box, not a jumb superbox")
    return header


def read_store(data: bytes) -> list[JumbfBoxSummary]:
    """Walk `data` as exactly one `jumb` superbox and return every box in it, depth first.

    Raises `JumbfError` when the bytes are not one well-formed `jumb` box; what the box describes is
    not checked here (`classify_store` says which kind it is).
    """
    header = _superbox_header(data)
    if header.end != len(data):
        raise JumbfError(f"the jumb box is {header.end} bytes but the data runs {len(data)} bytes")
    boxes: list[JumbfBoxSummary] = []
    _walk(data, 0, len(data), 0, boxes)
    return boxes


def classify_store(data: bytes) -> str:
    """The manifest kind of a `jumb` superbox, which classifies and never refuses a well-formed store.

    `C2PA_KIND` when its description carries the C2PA manifest-store UUID and label, else `JUMBF_KIND`.

    Raises `JumbfError` when the bytes do not open with a `jumb` box described by a `jumd` box.
    """
    header = _superbox_header(data)
    description = _first_description(data, header)
    if description.uuid == C2PA_STORE_UUID and description.label == C2PA_STORE_LABEL:
        return C2PA_KIND
    return JUMBF_KIND
