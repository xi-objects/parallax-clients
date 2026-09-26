"""`ParallaxClientOptions` never prints its secrets."""

from __future__ import annotations

from xio_parallax_client import ParallaxClientOptions


def test_repr_and_str_omit_account_token_and_admin_key() -> None:
    options = ParallaxClientOptions(
        account_token="distinctive-account-token-9f3c",
        admin_key="distinctive-admin-key-7b1e",
        base_url="https://distinctive-base.example.test",
    )

    text_repr = repr(options)
    text_str = str(options)

    assert "distinctive-account-token-9f3c" not in text_repr
    assert "distinctive-admin-key-7b1e" not in text_repr
    assert "distinctive-account-token-9f3c" not in text_str
    assert "distinctive-admin-key-7b1e" not in text_str
