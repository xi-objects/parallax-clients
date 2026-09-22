"""The hand-written layer of the XI Parallax Python client.

Wraps `xio_parallax_client.generated` (openapi-python-client output, never edited) with the three
things a generator cannot give: multipart parts named `manifest[<kind>]`, the slot conversations
as one call each, and typed `application/problem+json` refusals.
"""

from .async_client import AsyncParallaxClient
from .c2pa import (
    C2paCarrier,
    C2paComparison,
    C2paComparisonOutcome,
    EmbeddedC2paResult,
    EmbeddedC2paStore,
    JumbfBoxSummary,
    as_manifest_part,
    compare_with_record,
    detect_embedded_c2pa,
)
from .client import ParallaxClient
from .hashing import sha256_hex
from .multipart import ImageUpload, ManifestForm, ManifestPart
from .options import ParallaxClientOptions, UploadBatching
from .problems import ParallaxClientError, ParallaxProblem
from .slots import (
    LookupBatchOptions,
    LookupBatchResult,
    RecordWaitOptions,
    RegisterBatchOptions,
    RegisterBatchResult,
    RegistrationItem,
)

__all__ = [
    "AsyncParallaxClient",
    "C2paCarrier",
    "C2paComparison",
    "C2paComparisonOutcome",
    "EmbeddedC2paResult",
    "EmbeddedC2paStore",
    "ImageUpload",
    "JumbfBoxSummary",
    "LookupBatchOptions",
    "LookupBatchResult",
    "ManifestForm",
    "ManifestPart",
    "ParallaxClient",
    "ParallaxClientError",
    "ParallaxClientOptions",
    "ParallaxProblem",
    "RecordWaitOptions",
    "RegisterBatchOptions",
    "RegisterBatchResult",
    "RegistrationItem",
    "UploadBatching",
    "as_manifest_part",
    "compare_with_record",
    "detect_embedded_c2pa",
    "sha256_hex",
]
