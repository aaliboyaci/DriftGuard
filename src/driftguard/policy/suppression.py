"""Suppression/waiver system for policy decisions.

Allows teams to suppress or demote specific drift detections by pattern,
providing a mechanism for known/accepted schema changes to not block CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from fnmatch import fnmatch
from pathlib import Path

import yaml

from driftguard.policy.models import PolicyDecision, Severity


@dataclass
class SuppressionRule:
    """A single suppression rule that can match and modify policy decisions."""

    resource: str | None = None
    path: str | None = None
    category: str | None = None
    severity_override: str | None = None
    reason: str = ""
    owner: str = ""
    expires_at: str | None = None

    def is_expired(self) -> bool:
        """Check if this rule has passed its expiry date."""
        if self.expires_at is None:
            return False
        try:
            expiry = date.fromisoformat(self.expires_at)
            return date.today() > expiry
        except ValueError:
            return False

    def matches(self, decision: PolicyDecision) -> bool:
        """Check if this rule matches the given policy decision.

        All specified criteria must match (AND logic).
        """
        if self.is_expired():
            return False

        if self.resource is not None and not fnmatch(decision.event.resource_name, self.resource):
            return False

        if self.path is not None and not fnmatch(decision.event.description, f"*{self.path}*"):
            return False

        return not (self.category is not None and decision.event.category.value != self.category)

    def validate(self) -> list[str]:
        """Return validation errors for this rule."""
        errors: list[str] = []
        if not self.reason:
            errors.append("Suppression rule missing 'reason'")
        if not self.owner:
            errors.append("Suppression rule missing 'owner'")
        if self.severity_override is not None:
            valid_overrides = {"breaking", "warning", "info", "ignore"}
            if self.severity_override not in valid_overrides:
                errors.append(
                    f"Invalid severity_override '{self.severity_override}'; "
                    f"must be one of: {', '.join(sorted(valid_overrides))}"
                )
        return errors


@dataclass
class SuppressionFile:
    """Manages a collection of suppression rules loaded from a YAML file."""

    rules: list[SuppressionRule] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> SuppressionFile:
        """Load .driftguardignore YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        if data is None:
            return cls(rules=[])

        raw_rules = data.get("suppressions", [])
        rules: list[SuppressionRule] = []
        for raw in raw_rules:
            rule = SuppressionRule(
                resource=raw.get("resource"),
                path=raw.get("path"),
                category=raw.get("category"),
                severity_override=raw.get("severity_override"),
                reason=raw.get("reason", ""),
                owner=raw.get("owner", ""),
                expires_at=raw.get("expires_at"),
            )
            # Normalize expires_at to string if it's a date object
            if isinstance(rule.expires_at, (date, datetime)):
                rule.expires_at = rule.expires_at.isoformat()
            rules.append(rule)

        return cls(rules=rules)

    def apply(self, decisions: list[PolicyDecision]) -> list[PolicyDecision]:
        """Apply suppressions: demote severity or remove decisions.

        Returns a new list of PolicyDecision objects with suppressions applied.
        Decisions matching a rule with severity_override="ignore" are removed.
        """
        result: list[PolicyDecision] = []
        for decision in decisions:
            matched_rule = self._find_matching_rule(decision)
            if matched_rule is None:
                result.append(decision)
                continue

            if matched_rule.severity_override == "ignore":
                # Remove the decision entirely
                continue

            if matched_rule.severity_override is not None:
                # Demote to the specified severity
                new_severity = Severity(matched_rule.severity_override)
                suppressed = PolicyDecision(
                    event=decision.event,
                    severity=new_severity,
                    reason=f"[suppressed] {decision.reason} (suppressed by: {matched_rule.reason})",
                    override=True,
                )
                result.append(suppressed)
            else:
                result.append(decision)

        return result

    def expired_rules(self) -> list[SuppressionRule]:
        """Return rules past their expiry date."""
        return [rule for rule in self.rules if rule.is_expired()]

    def validate(self) -> list[str]:
        """Return all validation errors across all rules."""
        errors: list[str] = []
        for i, rule in enumerate(self.rules):
            for error in rule.validate():
                errors.append(f"Rule {i}: {error}")
        return errors

    def _find_matching_rule(self, decision: PolicyDecision) -> SuppressionRule | None:
        """Find the first matching rule for a decision."""
        for rule in self.rules:
            if rule.matches(decision):
                return rule
        return None
