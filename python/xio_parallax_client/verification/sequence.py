"""A published sequence record's two checks: its sequence hash and its summary signature (PC-120).

The sequence hash, BLAKE3-256 over the listed frame hashes in order, proves the ordered frame hashes. The
summary signature proves which frame id and which image each frame hash stands for, the sizes and the
verdict: the record's own leaf signs xio_parallax_common's version-1 sequence summary preimage, laid out
here exactly as that repository's px-frame.md ("The sequence summary preimage") defines it.
"""

from __future__ import annotations

import base64
import binascii
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import blake3
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .errors import VerificationRefused
from .report import CheckOutcome, VerificationCheck

SUMMARY_PREIMAGE_VERSION = 1
"""The only summary preimage version implemented; its byte leads the preimage."""

SUMMARY_PREIMAGE_TAG = b"px-sequence-summary"
"""The preimage's domain-separation tag, behind a big-endian uint16 length."""

SUMMARY_PREIMAGE_LENGTH = 115
"""Every version-1 summary preimage's length, whatever the sequence's length."""

SEQUENCE_HASH_CHECK = "sequenceHash"
SUMMARY_SIGNATURE_CHECK = "summarySignature"

_HASH_LENGTH = 32
_PASSED = CheckOutcome.PASSED
_FAILED = CheckOutcome.FAILED


@dataclass(frozen=True)
class SummaryFrame:
    """One frame's contribution to the frames digest: its id, image content hash and PX frame hash."""

    frame_id: int
    original_image_hash: bytes
    frame_hash: bytes


class SequenceSummaryPreimage:
    """Builds the version-1 sequence summary preimage, every integer big-endian."""

    @staticmethod
    def frames_digest(frames: list[SummaryFrame]) -> bytes:
        """BLAKE3-256 over every frame's 72-byte entry, i64 frame id then the two hashes, in walk order."""
        if not frames:
            raise ValueError("a summary with no frames has no preimage: a committed sequence carries at least one BODY")
        entries = bytearray()
        for index, frame in enumerate(frames):
            _require_hash(frame.original_image_hash, f"frame {index} originalImageHash")
            _require_hash(frame.frame_hash, f"frame {index} frameHash")
            entries += struct.pack(">q", frame.frame_id) + frame.original_image_hash + frame.frame_hash
        return blake3.blake3(bytes(entries)).digest()

    @staticmethod
    def build(
        sequence_hash: bytes,
        expected_size: int | None,
        final_size: int,
        connected: bool,
        sealed: bool,
        reach: int,
        frames_received: int,
        frames: list[SummaryFrame],
    ) -> bytes:
        """The 115-byte preimage: version, tag, sequence hash, sizes, verdict, frame count and frames digest."""
        _require_hash(sequence_hash, "sequenceHash")
        if (expected_size is not None and expected_size < 0) or final_size < 0 or frames_received < 0:
            raise ValueError("a summary's sizes and counts are never negative")
        preimage = (
            bytes([SUMMARY_PREIMAGE_VERSION])
            + struct.pack(">H", len(SUMMARY_PREIMAGE_TAG))
            + SUMMARY_PREIMAGE_TAG
            + struct.pack(">H", _HASH_LENGTH)
            + sequence_hash
            + bytes([0 if expected_size is None else 1])
            + struct.pack(">i", expected_size or 0)
            + struct.pack(">i", final_size)
            + bytes([1 if connected else 0, 1 if sealed else 0])
            + struct.pack(">q", reach)
            + struct.pack(">i", frames_received)
            + struct.pack(">I", len(frames))
            + SequenceSummaryPreimage.frames_digest(frames)
        )
        assert len(preimage) == SUMMARY_PREIMAGE_LENGTH
        return preimage


def _require_hash(value: bytes, name: str) -> None:
    if len(value) != _HASH_LENGTH:
        raise ValueError(f"{name} is {len(value)} bytes; every hash in a summary is {_HASH_LENGTH}")


def _field(source: Any, key: str, attribute: str) -> Any:
    """One field off a generated model or its plain JSON dict; UNSET reads as None."""
    value = source.get(key) if isinstance(source, Mapping) else getattr(source, attribute, None)
    return None if value is None or type(value).__name__ == "Unset" else value


def _integer(value: Any) -> int | None:
    """The generator renders 64-bit integers as `int | str`; a digit string reads as its integer."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _hex32(value: Any) -> bytes | None:
    if not isinstance(value, str):
        return None
    try:
        decoded = bytes.fromhex(value)
    except ValueError:
        return None
    return decoded if len(decoded) == _HASH_LENGTH else None


def _read_frames(sequence: Any) -> tuple[list[SummaryFrame] | None, str | None]:
    listed = _field(sequence, "frames", "frames")
    if not listed:
        return None, "the sequence lists no frames; a committed sequence carries at least one BODY"
    frames: list[SummaryFrame] = []
    for index, frame in enumerate(listed):
        frame_id = _integer(_field(frame, "frameId", "frame_id"))
        image_hash = _hex32(_field(frame, "originalImageHash", "original_image_hash"))
        frame_hash = _hex32(_field(frame, "frameHash", "frame_hash"))
        if frame_id is None or image_hash is None or frame_hash is None:
            return None, (
                f"listed frame {index} lacks a frame id, or its originalImageHash or frameHash "
                "is not a 32-byte hex hash"
            )
        frames.append(SummaryFrame(frame_id, image_hash, frame_hash))
    return frames, None


def record_sequence(record: Any) -> Any:
    """A record's `sequence` (generated model or JSON dict), or None for an image or frame record."""
    return _field(record, "sequence", "sequence")


def sequence_checks(sequence: Any, content_hash: bytes, key: Ed25519PublicKey | None) -> list[VerificationCheck]:
    """The `sequenceHash` and `summarySignature` checks for a published sequence record.

    Raises `VerificationRefused` for a summary preimage version other than 1: a version this verifier
    does not lay out is refused, never guessed at.
    """
    version = _integer(_field(sequence, "summaryPreimageVersion", "summary_preimage_version"))
    if version is not None and version != SUMMARY_PREIMAGE_VERSION:
        raise VerificationRefused(
            f"summaryPreimageVersion {version} is not implemented (only {SUMMARY_PREIMAGE_VERSION})"
        )
    frames, problem = _read_frames(sequence)
    return [
        _sequence_hash_check(frames, problem, content_hash),
        _summary_signature_check(sequence, version, frames, problem, content_hash, key),
    ]


def _sequence_hash_check(
    frames: list[SummaryFrame] | None, problem: str | None, content_hash: bytes
) -> VerificationCheck:
    if frames is None:
        return VerificationCheck(SEQUENCE_HASH_CHECK, _FAILED, problem or "")
    recomputed = blake3.blake3(b"".join(frame.frame_hash for frame in frames)).digest()
    if recomputed == content_hash:
        return VerificationCheck(
            SEQUENCE_HASH_CHECK, _PASSED, "BLAKE3-256 over the listed frame hashes, in order, equals contentHash"
        )
    return VerificationCheck(
        SEQUENCE_HASH_CHECK, _FAILED, f"BLAKE3-256 over the listed frame hashes is {recomputed.hex()}"
    )


def _summary_signature_check(
    sequence: Any,
    version: int | None,
    frames: list[SummaryFrame] | None,
    problem: str | None,
    content_hash: bytes,
    key: Ed25519PublicKey | None,
) -> VerificationCheck:
    signature_text = _field(sequence, "summarySignature", "summary_signature")
    if version is None and not signature_text:
        return VerificationCheck(
            SUMMARY_SIGNATURE_CHECK,
            CheckOutcome.NOT_PERFORMED,
            "the record declares no summary signature (a sequence committed before summary signing): "
            "each frame's id and image hash are reported, not proven",
        )
    if version is None or not signature_text:
        return VerificationCheck(
            SUMMARY_SIGNATURE_CHECK,
            _FAILED,
            "the record declares a summary signature without its version, or the reverse",
        )
    if frames is None:
        return VerificationCheck(SUMMARY_SIGNATURE_CHECK, _FAILED, problem or "")

    verdict = _field(sequence, "verdict", "verdict")
    final_size = _integer(_field(sequence, "finalSize", "final_size"))
    connected = None if verdict is None else _field(verdict, "connected", "connected")
    sealed = None if verdict is None else _field(verdict, "sealed", "sealed")
    reach = None if verdict is None else _integer(_field(verdict, "reach", "reach"))
    frames_received = None if verdict is None else _integer(_field(verdict, "framesReceived", "frames_received"))
    if (
        final_size is None
        or not isinstance(connected, bool)
        or not isinstance(sealed, bool)
        or reach is None
        or frames_received is None
    ):
        return VerificationCheck(
            SUMMARY_SIGNATURE_CHECK,
            _FAILED,
            "the summary lacks its final size or a verdict field, so its preimage cannot be built",
        )

    try:
        preimage = SequenceSummaryPreimage.build(
            content_hash,
            _integer(_field(sequence, "expectedSize", "expected_size")),
            final_size,
            connected,
            sealed,
            reach,
            frames_received,
            frames,
        )
    except ValueError as exc:
        return VerificationCheck(SUMMARY_SIGNATURE_CHECK, _FAILED, f"the summary preimage cannot be built: {exc}")

    if key is None:
        return VerificationCheck(SUMMARY_SIGNATURE_CHECK, _FAILED, "publicKey is not a raw 32-byte Ed25519 key")
    try:
        signature = base64.b64decode(signature_text, validate=True)
        key.verify(signature, preimage)
    except (binascii.Error, ValueError):
        return VerificationCheck(SUMMARY_SIGNATURE_CHECK, _FAILED, "summarySignature is not standard base64")
    except InvalidSignature:
        return VerificationCheck(
            SUMMARY_SIGNATURE_CHECK, _FAILED, "Ed25519 signature does not verify over the summary preimage"
        )
    return VerificationCheck(SUMMARY_SIGNATURE_CHECK, _PASSED, "Ed25519 signature verifies over the summary preimage")
