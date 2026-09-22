"""Per-carrier extraction of an embedded C2PA manifest store, per the C2PA specification's embedding rules.

Each extractor returns the store's bytes verbatim (or None when the carrier holds none) and raises
`CarrierError` when the carrier itself is malformed. None of them parses the claims inside the store.
"""

from __future__ import annotations

import struct
import zlib
from collections import defaultdict

from .jumbf import is_c2pa_store

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_STORE_CHUNK = b"caBX"
_WEBP_STORE_CHUNK = b"C2PA"
_TIFF_STORE_TAG = 0xCD41
_JPEG_APP11 = 0xEB
_JPEG_SOS = 0xDA
_JPEG_EOI = 0xD9
_JPEG_STANDALONE = frozenset({0x01, *range(0xD0, 0xD8)})
_TIFF_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}


class CarrierError(ValueError):
    """The carrier file is malformed where the store would be read from; the message says where."""


def _app11_segments(data: bytes) -> list[bytes]:
    """Return the payload of every APP11 segment before the first SOS."""
    payloads: list[bytes] = []
    offset = 2
    while offset < len(data):
        if data[offset] != 0xFF:
            raise CarrierError(f"expected a JPEG marker at offset {offset}")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            raise CarrierError("JPEG ends inside a marker")
        marker = data[offset]
        offset += 1
        if marker in _JPEG_STANDALONE:
            continue
        if marker in (_JPEG_SOS, _JPEG_EOI):
            break
        if offset + 2 > len(data):
            raise CarrierError(f"JPEG segment 0xFF{marker:02X} has a truncated length")
        (length,) = struct.unpack_from(">H", data, offset)
        if length < 2 or offset + length > len(data):
            raise CarrierError(f"JPEG segment 0xFF{marker:02X} at offset {offset} overruns the file")
        if marker == _JPEG_APP11:
            payloads.append(data[offset + 2 : offset + length])
        offset += length
    return payloads


def _app11_header_end(payload: bytes) -> int:
    """Where the LBox/TBox (and XLBox) header an APP11 JUMBF segment repeats after En and Z ends."""
    (lbox,) = struct.unpack_from(">I", payload, 8)
    end = 24 if lbox == 1 else 16
    if len(payload) < end:
        raise CarrierError("APP11 JUMBF segment is shorter than its repeated box header")
    return end


def extract_jpeg(data: bytes) -> bytes | None:
    """Reassemble the C2PA store from its APP11 segments: per En, the repeated header then the chunks by Z."""
    headers: dict[int, bytes] = {}
    chunks: dict[int, dict[int, bytes]] = defaultdict(dict)
    for payload in _app11_segments(data):
        if not payload.startswith(b"JP") or len(payload) < 16 or payload[12:16] != b"jumb":
            continue
        en, z = struct.unpack_from(">HI", payload, 2)
        header_end = _app11_header_end(payload)
        header = payload[8:header_end]
        if headers.setdefault(en, header) != header:
            raise CarrierError(f"APP11 segments of box instance {en} repeat different LBox/TBox headers")
        if z in chunks[en]:
            raise CarrierError(f"APP11 box instance {en} repeats packet sequence number {z}")
        chunks[en][z] = payload[header_end:]
    stores: list[bytes] = []
    for en, header in headers.items():
        superbox = header + b"".join(chunks[en][z] for z in sorted(chunks[en]))
        if is_c2pa_store(superbox):
            stores.append(superbox)
    if len(stores) > 1:
        raise CarrierError(f"JPEG carries {len(stores)} C2PA manifest stores; the specification allows one")
    return stores[0] if stores else None


def extract_png(data: bytes) -> bytes | None:
    """Return the data of the `caBX` chunk, checking each chunk's CRC up to IEND."""
    offset = len(PNG_SIGNATURE)
    found: bytes | None = None
    while offset < len(data):
        if offset + 12 > len(data):
            raise CarrierError(f"PNG chunk at offset {offset} is truncated")
        length, chunk_type = struct.unpack_from(">I4s", data, offset)
        end = offset + 12 + length
        if end > len(data):
            raise CarrierError(f"PNG chunk {chunk_type!r} at offset {offset} overruns the file")
        body = data[offset + 8 : offset + 8 + length]
        (crc,) = struct.unpack_from(">I", data, offset + 8 + length)
        if zlib.crc32(chunk_type + body) != crc:
            raise CarrierError(f"PNG chunk {chunk_type.decode('latin-1')!r} at offset {offset} fails its CRC")
        if chunk_type == _PNG_STORE_CHUNK:
            if found is not None:
                raise CarrierError("PNG carries more than one caBX chunk; the specification allows one")
            found = body
        if chunk_type == b"IEND":
            return found
        offset = end
    raise CarrierError("PNG ends without an IEND chunk")


def extract_webp(data: bytes) -> bytes | None:
    """Return the data of the RIFF `C2PA` chunk of a WebP file."""
    (riff_size,) = struct.unpack_from("<I", data, 4)
    end = 8 + riff_size
    if end > len(data):
        raise CarrierError(f"RIFF declares {riff_size} bytes but the file is shorter")
    offset = 12
    while offset < end:
        if offset + 8 > end:
            raise CarrierError(f"RIFF chunk header at offset {offset} is truncated")
        fourcc, size = struct.unpack_from("<4sI", data, offset)
        body_end = offset + 8 + size
        if body_end > end:
            raise CarrierError(f"RIFF chunk {fourcc!r} at offset {offset} overruns the file")
        if fourcc == _WEBP_STORE_CHUNK:
            return data[offset + 8 : body_end]
        offset = body_end + (size & 1)
    return None


def extract_tiff(data: bytes) -> bytes | None:
    """Return the bytes of tag 52545 (0xCD41) in the first IFD of a classic (not Big) TIFF or DNG."""
    order = "<" if data[:2] == b"II" else ">"
    if len(data) < 8:
        raise CarrierError("TIFF header is truncated")
    (ifd,) = struct.unpack_from(order + "I", data, 4)
    if ifd + 2 > len(data):
        raise CarrierError(f"TIFF IFD0 offset {ifd} is outside the file")
    (count,) = struct.unpack_from(order + "H", data, ifd)
    if ifd + 2 + 12 * count > len(data):
        raise CarrierError("TIFF IFD0 overruns the file")
    for index in range(count):
        entry = ifd + 2 + 12 * index
        tag, field_type, value_count = struct.unpack_from(order + "HHI", data, entry)
        if tag != _TIFF_STORE_TAG:
            continue
        size = _TIFF_TYPE_SIZES.get(field_type, 0) * value_count
        if size == 0:
            raise CarrierError(f"TIFF tag 0xCD41 has an unusable field type {field_type}")
        if size <= 4:
            return data[entry + 8 : entry + 8 + size]
        (value_offset,) = struct.unpack_from(order + "I", data, entry + 8)
        if value_offset + size > len(data):
            raise CarrierError("TIFF tag 0xCD41 points outside the file")
        return data[value_offset : value_offset + size]
    return None
