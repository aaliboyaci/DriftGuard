"""Policy decision models.

The policy engine evaluates each DiffEvent and produces a PolicyDecision
with a severity level and human-readable explanation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from driftguard.diff.events import DiffEvent


class Severity(str, Enum):
    """Risk severity level for a schema change."""

    BREAKING = "breaking"
    WARNING = "warning"
    INFO = "info"


class PolicyMode(str, Enum):
    """Policy evaluation mode controlling strictness."""

    DEFAULT = "default"
    STRICT = "strict"
    LENIENT = "lenient"
    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"


class PolicyDecision(BaseModel):
    """Risk assessment for a single DiffEvent."""

    event: DiffEvent
    severity: Severity
    reason: str = Field(description="Why this severity was assigned")
    override: bool = Field(default=False, description="Whether this was overridden by user policy")


class PolicyResult(BaseModel):
    """Aggregated result of policy evaluation across all diff events."""

    decisions: list[PolicyDecision] = Field(default_factory=list)

    @property
    def has_breaking(self) -> bool:
        return any(d.severity == Severity.BREAKING for d in self.decisions)

    @property
    def has_warnings(self) -> bool:
        return any(d.severity == Severity.WARNING for d in self.decisions)

    @property
    def breaking_count(self) -> int:
        return sum(1 for d in self.decisions if d.severity == Severity.BREAKING)

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.decisions if d.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for d in self.decisions if d.severity == Severity.INFO)

    def by_severity(self, severity: Severity) -> list[PolicyDecision]:
        return [d for d in self.decisions if d.severity == severity]

    @property
    def exit_code(self) -> int:
        """Return non-zero if there are breaking changes (for CI gate)."""
        return 1 if self.has_breaking else 0
