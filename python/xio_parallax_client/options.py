"""Client configuration: the account credential, the admin key, and the caller-stated batching caps."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class UploadBatching:
    """The caller-stated caps for a slot upload batch.

    The server's own request-byte and image-count caps are operator configuration and are not
    carried in the OpenAPI document, so a batching client must be told them explicitly rather than
    guess: `ParallaxClientOptions.batching` stays `None` until the caller sets it.
    """

    max_request_bytes: int
    max_images_per_request: int


@dataclass(frozen=True, slots=True)
class ParallaxClientOptions:
    """Configuration for a `ParallaxClient` or `AsyncParallaxClient`.

    `account_token` is sent as a `Bearer` credential and `admin_key` as `X-Admin-Key`; either may
    be left unset when the caller only needs the other. `batching` is required by
    `register_batch`/`lookup_batch` and is never defaulted to a guessed value.
    """

    account_token: str | None = field(default=None, repr=False)
    admin_key: str | None = field(default=None, repr=False)
    base_url: str = "https://api.parallax.xiobjects.com"
    batching: UploadBatching | None = None
