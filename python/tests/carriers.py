"""Test helpers: a synthetic C2PA manifest store and the carriers (JPEG, PNG, WebP, TIFF) that embed it."""

from __future__ import annotations

import struct
import zlib

C2PA_UUID = bytes.fromhex("6332706100110010800000AA00389B71")
CBOR_UUID = bytes.fromhex("63626F7200110010800000AA00389B71")


def box(box_type: bytes, payload: bytes) -> bytes:
    """One JUMBF box: LBox, TBox, payload."""
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def description(uuid: bytes, label: str) -> bytes:
    """A `jumd` box with the label toggle set (plus the requestable bit, as C2PA writes it)."""
    return box(b"jumd", uuid + b"\x03" + label.encode("utf-8") + b"\x00")


def superbox(uuid: bytes, label: str, *children: bytes) -> bytes:
    """A `jumb` superbox: its description, then its children."""
    return box(b"jumb", description(uuid, label) + b"".join(children))


def synthetic_store() -> bytes:
    """A C2PA store holding one manifest superbox with a claim (`cbor`) box inside a nested superbox."""
    claim = superbox(CBOR_UUID, "c2pa.claim", box(b"cbor", bytes([0xA1, 0x61, 0x61, 0x01]) * 40))
    manifest = superbox(C2PA_UUID, "urn:uuid:test-manifest", claim)
    return superbox(C2PA_UUID, "c2pa", manifest)


def _segment(marker: int, payload: bytes) -> bytes:
    """One JPEG marker segment with its big-endian length."""
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def jpeg(store: bytes | None, pieces: int = 3, order: list[int] | None = None) -> bytes:
    """A minimal JPEG: SOI, APP0, the store split across APP11 segments (in `order` of Z), SOS stub, EOI."""
    out = bytes([0xFF, 0xD8]) + _segment(0xE0, b"JFIF" + bytes([0, 1, 1, 0, 0, 1, 0, 1, 0, 0]))
    if store is not None:
        header, body = store[:8], store[8:]
        size = -(-len(body) // pieces)
        chunks = [body[i * size : (i + 1) * size] for i in range(pieces)]
        for z in order or list(range(1, pieces + 1)):
            out += _segment(0xEB, b"JP" + struct.pack(">HI", 1, z) + header + chunks[z - 1])
    return out + _segment(0xDA, bytes([1, 1, 0, 0, 0x3F, 0])) + bytes([0, 0xFF, 0xD9])


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """One PNG chunk with its CRC over type and data."""
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data))


def png(store: bytes | None) -> bytes:
    """A PNG: signature, IHDR, a `caBX` chunk holding `store` (when given), IEND, all with correct CRCs."""
    signature = bytes([0x89]) + b"PNG" + bytes([0x0D, 0x0A, 0x1A, 0x0A])
    out = signature + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    if store is not None:
        out += _png_chunk(b"caBX", store)
    return out + _png_chunk(b"IEND", b"")


def _riff_chunk(fourcc: bytes, data: bytes) -> bytes:
    """One RIFF chunk, padded to an even length."""
    return fourcc + struct.pack("<I", len(data)) + data + (bytes(1) if len(data) % 2 else b"")


def webp(store: bytes | None) -> bytes:
    """A WebP RIFF: a VP8L stub chunk and a `C2PA` chunk holding `store` (when given)."""
    body = b"WEBP" + _riff_chunk(b"VP8L", bytes([0x2F, 0, 0, 0, 0]))
    if store is not None:
        body += _riff_chunk(b"C2PA", store)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def tiff(store: bytes) -> bytes:
    """A little-endian TIFF whose IFD0 holds tag 0xCD41 (UNDEFINED) pointing at `store`."""
    ifd = struct.pack("<H", 1) + struct.pack("<HHII", 0xCD41, 7, len(store), 26) + struct.pack("<I", 0)
    return b"II*" + bytes(1) + struct.pack("<I", 8) + ifd + store
