"""Shared test fixtures: a fake base URL and options factories for the hand-written client layer."""

from __future__ import annotations

import pytest
from xio_parallax_client import ParallaxClientOptions, UploadBatching

BASE_URL = "https://parallax.test"


@pytest.fixture
def options() -> ParallaxClientOptions:
    """Options with an account token and generous batching caps, against the fake base URL."""
    return ParallaxClientOptions(
        account_token="test-token",
        base_url=BASE_URL,
        batching=UploadBatching(max_request_bytes=10_000_000, max_images_per_request=50),
    )


@pytest.fixture
def unbatched_options() -> ParallaxClientOptions:
    """Options with no batching, to exercise the batch-call refusal."""
    return ParallaxClientOptions(account_token="test-token", base_url=BASE_URL, batching=None)
