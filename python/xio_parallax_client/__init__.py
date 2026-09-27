"""The hand-written layer of the XI Parallax Python client.

Wraps `xio_parallax_client.generated` (openapi-python-client output, never edited) with the three
things a generator cannot give: multipart parts named `manifest[<kind>]`, the slot conversations
as one call each, and typed `application/problem+json` refusals; plus the embedded JUMBF manifest
store detection and the manifest selection resolved over a whole collection before anything is sent.
"""

# PC-114: the public sequence conversation and frame source names
from .async_client import AsyncParallaxClient
from .c2pa import (
    C2paCarrier,
    C2paComparison,
    C2paComparisonOutcome,
    EmbeddedC2paOutcome,
    EmbeddedC2paResult,
    EmbeddedC2paStore,
    JumbfBoxSummary,
    as_manifest_part,
    compare_with_record,
    detect_embedded_c2pa,
)
from .client import ParallaxClient
from .frames import AsyncSequenceFrameSource, SequenceFrameInput, SequenceFrameSource
from .hashing import sha256_hex
from .manifests import (
    NO_MANIFESTS,
    ManifestRefusal,
    ManifestRefusalError,
    ManifestRequest,
    ManifestSelection,
    SidecarManifest,
    resolve_image_manifests,
    resolve_manifests,
)
from .multipart import ImageUpload, ManifestForm, ManifestPart
from .options import ParallaxClientOptions, UploadBatching
from .problems import ParallaxClientError, ParallaxProblem, SequencesNotEnabled
from .sequences import (
    EncodedFrame,
    OpenedSequence,
    SequenceBatching,
    SequenceCommitError,
    SequenceHandle,
    SequenceOpenRequest,
    SequenceRegisterOptions,
    SequenceRegisterResult,
    SequenceVerdictError,
    VerdictCallback,
)
from .slots import (
    LookupBatchOptions,
    LookupBatchResult,
    RecordWaitOptions,
    RegisterBatchOptions,
    RegisterBatchResult,
    RegistrationItem,
)

__all__ = [
    "NO_MANIFESTS",
    "AsyncParallaxClient",
    "AsyncSequenceFrameSource",
    "C2paCarrier",
    "C2paComparison",
    "C2paComparisonOutcome",
    "EmbeddedC2paOutcome",
    "EmbeddedC2paResult",
    "EmbeddedC2paStore",
    "EncodedFrame",
    "ImageUpload",
    "JumbfBoxSummary",
    "LookupBatchOptions",
    "LookupBatchResult",
    "ManifestForm",
    "ManifestPart",
    "ManifestRefusal",
    "ManifestRefusalError",
    "ManifestRequest",
    "ManifestSelection",
    "OpenedSequence",
    "ParallaxClient",
    "ParallaxClientError",
    "ParallaxClientOptions",
    "ParallaxProblem",
    "RecordWaitOptions",
    "RegisterBatchOptions",
    "RegisterBatchResult",
    "RegistrationItem",
    "SequenceBatching",
    "SequenceCommitError",
    "SequenceFrameInput",
    "SequenceFrameSource",
    "SequenceHandle",
    "SequenceOpenRequest",
    "SequenceRegisterOptions",
    "SequenceRegisterResult",
    "SequenceVerdictError",
    "SequencesNotEnabled",
    "SidecarManifest",
    "UploadBatching",
    "VerdictCallback",
    "as_manifest_part",
    "compare_with_record",
    "detect_embedded_c2pa",
    "resolve_image_manifests",
    "resolve_manifests",
    "sha256_hex",
]
