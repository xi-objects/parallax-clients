"""The pinned trust roots a record's certificate chain must reach."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

import httpx
from cryptography import x509

from .errors import VerificationRefused

_NO_ROOTS = "Control not activated: no roots"


def _info_url(orbital_base_url: str) -> str:
    return orbital_base_url.rstrip("/") + "/info"


def _pinned_roots_from_info(body: Any) -> list[str]:
    if not isinstance(body, dict):
        raise VerificationRefused("Orbital /info did not return a JSON object")
    matches = [value for key, value in body.items() if isinstance(key, str) and key.lower() == "pinnedroots"]
    if not matches:
        raise VerificationRefused("Orbital /info carries no pinnedRoots property")
    roots = matches[0]
    if not isinstance(roots, list) or not all(isinstance(r, str) for r in roots):
        raise VerificationRefused("Orbital /info pinnedRoots is not an array of PEM strings")
    if not roots:
        raise VerificationRefused(_NO_ROOTS)
    return roots


class TrustRoots:
    """An in-memory pin of root certificates; never empty."""

    def __init__(self, certificates: Iterable[x509.Certificate]) -> None:
        """Pin the given root certificates; an empty set is refused."""
        self._certificates: tuple[x509.Certificate, ...] = tuple(certificates)
        if not self._certificates:
            raise VerificationRefused(_NO_ROOTS)

    @property
    def certificates(self) -> tuple[x509.Certificate, ...]:
        """The pinned root certificates."""
        return self._certificates

    @classmethod
    def from_pem(cls, pems: Iterable[str]) -> TrustRoots:
        """Pin every certificate found in the given PEM strings (each may hold several certificates)."""
        certificates: list[x509.Certificate] = []
        for pem in pems:
            certificates.extend(x509.load_pem_x509_certificates(pem.encode("ascii")))
        return cls(certificates)

    @classmethod
    def from_pem_file(cls, path: str | os.PathLike[str]) -> TrustRoots:
        """Pin every certificate in the PEM file at `path`."""
        with open(path, encoding="ascii") as handle:
            return cls.from_pem([handle.read()])

    @classmethod
    def from_orbital(cls, orbital_base_url: str, client: httpx.Client | None = None) -> TrustRoots:
        """GET `{orbital_base_url}/info` anonymously and pin its `pinnedRoots`.

        The URL should be https: the roots are trusted because they arrive over TLS once. HTTP errors
        propagate as `httpx` exceptions; an absent or empty `pinnedRoots` raises `VerificationRefused`.
        """
        if client is None:
            with httpx.Client() as owned:
                response = owned.get(_info_url(orbital_base_url))
        else:
            response = client.get(_info_url(orbital_base_url))
        response.raise_for_status()
        return cls.from_pem(_pinned_roots_from_info(response.json()))

    @classmethod
    async def from_orbital_async(cls, orbital_base_url: str, client: httpx.AsyncClient | None = None) -> TrustRoots:
        """Async form of `from_orbital`: GET `{orbital_base_url}/info` (should be https) and pin `pinnedRoots`."""
        if client is None:
            async with httpx.AsyncClient() as owned:
                response = await owned.get(_info_url(orbital_base_url))
        else:
            response = await client.get(_info_url(orbital_base_url))
        response.raise_for_status()
        return cls.from_pem(_pinned_roots_from_info(response.json()))
