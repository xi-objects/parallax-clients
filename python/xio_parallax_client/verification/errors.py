"""The refusal raised when a record cannot be verified at all."""

from __future__ import annotations


class VerificationRefused(Exception):
    """Raised when verification cannot start: an unimplemented algorithm or canonical version, or no trust roots."""
