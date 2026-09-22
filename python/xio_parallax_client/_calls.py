"""Shared, hand-written plumbing used by both `ParallaxClient` and `AsyncParallaxClient`.

These helpers hold no client state of their own; each is called with `self.options` or `self.api`
passed in explicitly, which is what lets `client.py` and `async_client.py` share them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from . import problems
from .generated.client import AuthenticatedClient
from .generated.models import SlotProgressResponse
from .options import ParallaxClientOptions

ProgressCallback = Callable[[SlotProgressResponse], None]

T = TypeVar("T")


def _build_api(options: ParallaxClientOptions) -> AuthenticatedClient:
    """Construct the generated `AuthenticatedClient`, with the admin key as an extra header when set."""
    headers: dict[str, str] = {}
    if options.admin_key is not None:
        headers["X-Admin-Key"] = options.admin_key
    return AuthenticatedClient(base_url=options.base_url, token=options.account_token or "", headers=headers)


def _parsed(response: Any) -> Any:
    """Return `response.parsed`, populated for every documented 2xx status this layer calls."""
    if response.parsed is None:
        raise problems.ParallaxClientError("the server returned an empty body for a documented success status")
    return response.parsed


def _require_batching(options: ParallaxClientOptions, call_name: str) -> Any:
    """Return `options.batching`, or raise since a batch call never guesses the server's caps."""
    if options.batching is None:
        raise problems.ParallaxClientError(
            f"{call_name} requires ParallaxClientOptions.batching (max_request_bytes, "
            "max_images_per_request); the server's caps are operator configuration and are never guessed."
        )
    return options.batching
