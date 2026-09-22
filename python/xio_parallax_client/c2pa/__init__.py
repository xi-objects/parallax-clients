"""C2PA detection and comparison, in the client: REST never inspects a file's content.

`detect_embedded_c2pa` finds and shows a store embedded in an image; `as_manifest_part` lets the
registrant attach it explicitly; `compare_with_record` checks a found image's store against the record.
"""

from __future__ import annotations

from .compare import compare_with_record
from .detector import as_manifest_part, detect_embedded_c2pa
from .models import (
    C2paCarrier,
    C2paComparison,
    C2paComparisonOutcome,
    EmbeddedC2paResult,
    EmbeddedC2paStore,
    JumbfBoxSummary,
)

__all__ = [
    "C2paCarrier",
    "C2paComparison",
    "C2paComparisonOutcome",
    "EmbeddedC2paResult",
    "EmbeddedC2paStore",
    "JumbfBoxSummary",
    "as_manifest_part",
    "compare_with_record",
    "detect_embedded_c2pa",
]
