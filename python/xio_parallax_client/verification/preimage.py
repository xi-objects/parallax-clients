"""Canonical version-2 preimages the record's Ed25519 signatures are made over."""

from __future__ import annotations

import struct

CANONICAL_VERSION: int = 2
_MAX_FIELD = 0xFFFF


def _u16(value: int) -> bytes:
    if not 0 <= value <= _MAX_FIELD:
        raise ValueError(f"value {value} does not fit a big-endian uint16")
    return struct.pack(">H", value)


def _field(data: bytes) -> bytes:
    return _u16(len(data)) + data


class CanonicalPreimage:
    """Builders for the canonical version-2 preimages; every length prefix is a big-endian uint16."""

    @staticmethod
    def manifest(content_hash: bytes, kind: str, manifest_hash: bytes) -> bytes:
        """Return `[0x02] ‖ len‖content_hash ‖ len‖kind(utf-8) ‖ len‖manifest_hash`, one manifest's preimage."""
        return bytes([CANONICAL_VERSION]) + _field(content_hash) + _field(kind.encode("utf-8")) + _field(manifest_hash)

    @staticmethod
    def collection(content_hash: bytes, entries: list[tuple[str, bytes]]) -> bytes:
        """Return `[0x02] ‖ len‖content_hash ‖ count(u16) ‖ (len‖kind ‖ len‖manifest_hash)*` in the given order."""
        parts = [bytes([CANONICAL_VERSION]), _field(content_hash), _u16(len(entries))]
        for kind, manifest_hash in entries:
            parts.append(_field(kind.encode("utf-8")))
            parts.append(_field(manifest_hash))
        return b"".join(parts)
