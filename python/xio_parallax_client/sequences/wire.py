"""The sequence wire words the register conversation branches on, spelled once.

Mirrors the .NET client's `SequenceWire`: the sequence states, the commit outcome and the commit
frame state read off the server's own responses, plus the ticket header name every route past open
sends.
"""

# PC-111: the sequence wire words, declared once

from __future__ import annotations

#: The header every route past open sends the sequence's ticket on.
TICKET_HEADER = "X-Sequence-Ticket"

#: A sequence still taking frames.
STATE_OPEN = "open"

#: A sequence END sealed; only fills are taken.
STATE_SEALED = "sealed"

#: A sequence the engine has taken.
STATE_COMMITTED = "committed"

#: A sequence the engine will not take back.
STATE_ABANDONED = "abandoned"

#: A commit that did not write the sequence record this call.
OUTCOME_INCOMPLETE = "incomplete"

#: A frame a commit has not published yet.
FRAME_STATE_NOT_PUBLISHED = "notPublished"
