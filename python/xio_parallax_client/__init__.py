"""The hand-written layer of the XI Parallax Python client.

Wraps `xio_parallax_client.generated` (openapi-python-client output, never edited) with the three
things a generator cannot give: multipart parts named `manifest[<kind>]`, the slot conversations
as one call each, and typed `application/problem+json` refusals.
"""

from .async_client import AsyncParallaxClient
from .client import ParallaxClient
from .hashing import sha256_hex
from .multipart import ImageUpload, ManifestForm, ManifestPart
from .options import ParallaxClientOptions, UploadBatching
from .problems import ParallaxClientError, ParallaxProblem
from .slots import (
    LookupBatchOptions,
    LookupBatchResult,
    RegisterBatchOptions,
    RegisterBatchResult,
    RegistrationItem,
)

__all__ = [
    "AsyncParallaxClient",
    "ImageUpload",
    "LookupBatchOptions",
    "LookupBatchResult",
    "ManifestForm",
    "ManifestPart",
    "ParallaxClient",
    "ParallaxClientError",
    "ParallaxClientOptions",
    "ParallaxProblem",
    "RegisterBatchOptions",
    "RegisterBatchResult",
    "RegistrationItem",
    "UploadBatching",
    "sha256_hex",
]
