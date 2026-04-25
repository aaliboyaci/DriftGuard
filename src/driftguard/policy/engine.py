"""Policy engine for risk classification.

Evaluates DiffEvents against a set of rules and produces PolicyDecisions
with severity levels (breaking/warning/info).
"""

from __future__ import annotations

from driftguard.diff.events import (
    ChangeCategory,
    DiffEvent,
    DiffResult,
    EnumValuesChanged,
    FieldAdded,
    NullableChanged,
    RequiredChanged,
    TypeChanged,
)
from driftguard.policy.models import PolicyDecision, PolicyResult, Severity

# Type transitions that are considered widening (potentially safe)
WIDENING_TRANSITIONS: set[tuple[str, str]] = {
    ("integer", "number"),
    ("integer", "string"),
    ("number", "string"),
    ("boolean", "string"),
}


def evaluate(diff_result: DiffResult) -> PolicyResult:
    """Evaluate all diff events and produce policy decisions."""
    decisions = [_evaluate_event(event) for event in diff_result.events]
    return PolicyResult(decisions=decisions)


def _evaluate_event(event: DiffEvent) -> PolicyDecision:
    """Evaluate a single diff event and return its policy decision."""
    match event.category:
        case ChangeCategory.RESOURCE_REMOVED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="Removing a resource breaks all consumers that depend on it",
            )
        case ChangeCategory.RESOURCE_ADDED:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="Adding a new resource is backward compatible",
            )
        case ChangeCategory.FIELD_REMOVED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="Consumers expecting this field will fail",
            )
        case ChangeCategory.FIELD_ADDED:
            return _evaluate_field_added(event)
        case ChangeCategory.FIELD_RENAMED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="Renaming a field is effectively a remove + add, breaking consumers",
            )
        case ChangeCategory.TYPE_CHANGED:
            return _evaluate_type_changed(event)
        case ChangeCategory.NULLABLE_CHANGED:
            return _evaluate_nullable_changed(event)
        case ChangeCategory.REQUIRED_CHANGED:
            return _evaluate_required_changed(event)
        case ChangeCategory.ENUM_VALUES_CHANGED:
            return _evaluate_enum_changed(event)


def _evaluate_field_added(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, FieldAdded)
    if event.required:
        return PolicyDecision(
            event=event,
            severity=Severity.BREAKING,
            reason="Adding a required field may break existing producers/consumers",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.INFO,
        reason="Adding an optional field is backward compatible",
    )


def _evaluate_type_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, TypeChanged)
    pair = (event.old_type, event.new_type)
    if pair in WIDENING_TRANSITIONS:
        return PolicyDecision(
            event=event,
            severity=Severity.WARNING,
            reason=f"Type widened from {event.old_type} to {event.new_type}; some consumers may accept this",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.BREAKING,
        reason=f"Type changed from {event.old_type} to {event.new_type}; parse and validation behavior changes",
    )


def _evaluate_nullable_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, NullableChanged)
    if not event.old_nullable and event.new_nullable:
        return PolicyDecision(
            event=event,
            severity=Severity.WARNING,
            reason="Field became nullable; consumers without null handling may fail",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.WARNING,
        reason="Field became non-nullable; existing null values will cause errors",
    )


def _evaluate_required_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, RequiredChanged)
    if event.old_required and not event.new_required:
        return PolicyDecision(
            event=event,
            severity=Severity.INFO,
            reason="Field became optional; backward compatible",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.BREAKING,
        reason="Field became required; existing data without this field will fail validation",
    )


def _evaluate_enum_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, EnumValuesChanged)
    if event.removed_values:
        return PolicyDecision(
            event=event,
            severity=Severity.BREAKING,
            reason=f"Enum values removed: {', '.join(event.removed_values)}; existing data with these values will be invalid",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.WARNING,
        reason=f"Enum values added: {', '.join(event.added_values)}; strict consumers may not handle new values",
    )
