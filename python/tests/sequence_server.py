"""PC-113: a fake sequence conversation server, a respx port of .NET's `SequenceConversationServer`.

Scripts one respx route per sequence endpoint: open answers a real HEAD frame encoded through the
default codec binding; frames answers each uploaded part's id (errata where scripted, and the
sealing verdict on the batch carrying `sealing_frame_id`); progress and commit are answered from
queues, one response per call, in the order pushed; gaps and results are fixed but replaceable.
Must be constructed inside an active `respx.mock` (as every route test in this suite already is).
"""

from __future__ import annotations

import base64
import email
import json
from dataclasses import dataclass
from email.message import Message
from uuid import UUID, uuid4

import httpx
import respx
from xio_parallax_client.frames.binding import default_frame_codec
from xio_parallax_client.frames.protocol import PxBodyHeader, PxEndHeader, PxFrameAccepted, PxFrameType, PxHeadHeader
from xio_parallax_client.sequences.models import OpenedSequence, SequenceHandle

#: The ticket the fake server's open answer carries; every later route echoes it in the test.
TICKET = "sequence-ticket-register"


# PC-113: one uploaded frame read back through the codec: its type, its id and its links
@dataclass(frozen=True, slots=True)
class DecodedSequenceFrame:
    """One uploaded frame decoded back through the codec: its type, id, and links."""

    frame_type: PxFrameType
    frame_id: int
    prev: int
    next: int | None


def multipart_parts(request: httpx.Request) -> list[tuple[str, bytes]]:
    """Parse an httpx multipart request body into `(part name, part bytes)` pairs, in order.

    A request with no parts at all carries no `Content-Type` (httpx omits multipart framing for
    an empty `files` list), which is itself a zero-part body.
    """
    content_type = request.headers.get("content-type")
    if content_type is None:
        return []
    raw = f"Content-Type: {content_type}\r\n\r\n".encode("ascii") + request.content
    message = email.message_from_bytes(raw)
    parts: list[tuple[str, bytes]] = []
    for part in message.get_payload():
        assert isinstance(part, Message)
        name = part.get_param("name", header="content-disposition")
        assert isinstance(name, str)
        body = part.get_payload(decode=True)
        assert isinstance(body, bytes)
        parts.append((name, body))
    return parts


# PC-113: a scripted sequence server for the register conversation, each route answered from its own script
class SequenceConversationServer:
    """A scripted fake sequence server behind respx; see the module docstring for its routes."""

    def __init__(self, base_url: str, head_frame_id: int = 0) -> None:
        """Mint a fresh sequence id and register every route this server answers."""
        self.sequence_id: UUID = uuid4()
        self.errata_frame_ids: set[int] = set()
        self.sealing_frame_id: int | None = None
        self.sealing_verdict_json: str | None = None
        self.gaps_json = '{"gaps": []}'
        self.progress: list[httpx.Response] = []
        self.commits: list[httpx.Response] = []
        self._codec = default_frame_codec()
        self._path_prefix = f"/sequences/{self.sequence_id}"
        head_header = PxHeadHeader(self.sequence_id, head_frame_id)
        self._head_frame = self._codec.encode(head_header, ()).frame
        respx.post(f"{base_url}/sequences").mock(side_effect=self._open)
        respx.post(f"{base_url}{self._path_prefix}/frames").mock(side_effect=self._frames)
        respx.get(f"{base_url}{self._path_prefix}/progress").mock(side_effect=lambda request: self.progress.pop(0))
        respx.get(f"{base_url}{self._path_prefix}/gaps").mock(side_effect=self._gaps)
        respx.post(f"{base_url}{self._path_prefix}/commit").mock(side_effect=lambda request: self.commits.pop(0))
        respx.get(f"{base_url}{self._path_prefix}/results").mock(side_effect=self._results)

    @property
    def opened(self) -> OpenedSequence:
        """The sequence as open answers it, for a resume test."""
        return OpenedSequence(SequenceHandle(self.sequence_id, TICKET), 0)

    @property
    def calls(self) -> list[str]:
        """Every request's method and path answered by this server, in order."""
        return [
            f"{call.request.method} {call.request.url.path}"
            for call in respx.calls
            if call.request.url.path == "/sequences" or call.request.url.path.startswith(f"{self._path_prefix}")
        ]

    def uploaded_frame_ids(self) -> list[list[int]]:
        """The part ids of every frames request, one list per request, in order."""
        return [[int(name) for name, _ in parts] for parts in self._frame_batches()]

    def decode_uploads(self) -> list[list[DecodedSequenceFrame]]:
        """Every frames request's frames decoded back through the codec, one list per request."""
        batches: list[list[DecodedSequenceFrame]] = []
        for parts in self._frame_batches():
            batch: list[DecodedSequenceFrame] = []
            for _name, body in parts:
                result = self._codec.decode(body)
                assert isinstance(result, PxFrameAccepted)
                header = result.frame.header
                if isinstance(header, PxBodyHeader):
                    batch.append(DecodedSequenceFrame(PxFrameType.BODY, header.frame_id, header.prev, header.next))
                elif isinstance(header, PxEndHeader):
                    batch.append(DecodedSequenceFrame(PxFrameType.END, header.frame_id, header.prev, None))
                else:
                    raise TypeError(f"{header.frame_type.name} is not a client frame")
            batches.append(batch)
        return batches

    def _frame_batches(self) -> list[list[tuple[str, bytes]]]:
        """Every frames request's raw multipart parts, one list per request, in order."""
        return [
            multipart_parts(call.request)
            for call in respx.calls
            if call.request.url.path == f"{self._path_prefix}/frames"
        ]

    def _open(self, request: httpx.Request) -> httpx.Response:
        """Answer open with this server's sequence id, ticket and real base64 HEAD frame."""
        return httpx.Response(
            201,
            json={
                "sequenceId": str(self.sequence_id),
                "ticket": TICKET,
                "headFrame": base64.b64encode(self._head_frame).decode("ascii"),
            },
        )

    def _frames(self, request: httpx.Request) -> httpx.Response:
        """Answer each uploaded part's id, errata where scripted, and the verdict when sealing."""
        ids = [int(name) for name, _ in multipart_parts(request)]
        frames = [{"frameId": frame_id, "errata": frame_id in self.errata_frame_ids} for frame_id in ids]
        verdict = None
        if self.sealing_frame_id in ids and self.sealing_verdict_json is not None:
            verdict = json.loads(self.sealing_verdict_json)
        return httpx.Response(201, json={"frames": frames, "verdict": verdict})

    def _gaps(self, request: httpx.Request) -> httpx.Response:
        """Answer the scripted gaps, read fresh so a test may change `gaps_json` mid-run."""
        return httpx.Response(200, content=self.gaps_json, headers={"content-type": "application/json"})

    def _results(self, request: httpx.Request) -> httpx.Response:
        """Answer a fixed final-results document."""
        return httpx.Response(
            200,
            json={
                "sequenceHash": "sequence-hash",
                "outcome": "registered",
                "finalSize": 3,
                "committedAt": "2026-09-26T00:00:00Z",
            },
        )
