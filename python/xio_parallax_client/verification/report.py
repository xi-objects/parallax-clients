"""The per-check verdict a verification returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CheckOutcome(Enum):
    """The outcome of one verification check."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RECOMPUTABLE = "not_recomputable"
    NOT_PERFORMED = "not_performed"


_UNPERFORMED = (CheckOutcome.NOT_RECOMPUTABLE, CheckOutcome.NOT_PERFORMED)


@dataclass(frozen=True)
class VerificationCheck:
    """One named check with its outcome and a human-readable detail."""

    name: str
    outcome: CheckOutcome
    detail: str


@dataclass
class VerificationReport:
    """Every check a verification ran, in order, with a verdict each."""

    checks: list[VerificationCheck] = field(default_factory=list)

    @property
    def performed(self) -> list[VerificationCheck]:
        """The checks that were performed (neither NOT_RECOMPUTABLE nor NOT_PERFORMED)."""
        return [c for c in self.checks if c.outcome not in _UNPERFORMED]

    @property
    def all_performed_passed(self) -> bool:
        """True when at least one check was performed and every performed check passed."""
        performed = self.performed
        return bool(performed) and all(c.outcome is CheckOutcome.PASSED for c in performed)

    @property
    def any_failed(self) -> bool:
        """True when any check failed."""
        return any(c.outcome is CheckOutcome.FAILED for c in self.checks)

    def outcome(self, name: str) -> CheckOutcome:
        """Return the outcome of the check named `name`; FAILED if any check of that name failed."""
        matches = [c for c in self.checks if c.name == name]
        if not matches:
            raise KeyError(f"no check named {name!r}")
        for wanted in (CheckOutcome.FAILED, CheckOutcome.NOT_RECOMPUTABLE, CheckOutcome.NOT_PERFORMED):
            if any(c.outcome is wanted for c in matches):
                return wanted
        return CheckOutcome.PASSED

    def passed(self, name: str) -> bool:
        """True when a check named `name` exists and every check of that name passed."""
        matches = [c for c in self.checks if c.name == name]
        return bool(matches) and all(c.outcome is CheckOutcome.PASSED for c in matches)
