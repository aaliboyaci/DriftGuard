"""Policy engine for risk classification.

Evaluates DiffEvents against a set of rules and produces PolicyDecisions
with severity levels (breaking/warning/info). Supports multiple policy modes.
"""

from __future__ import annotations

from driftguard.diff.events import (
    ChangeCategory,
    DiffEvent,
    DiffResult,
    EnumValuesChanged,
    FieldAdded,
    NestedEnumValuesChanged,
    NestedFieldAdded,
    NestedFieldRemoved,
    NestedFieldRequiredChanged,
    NestedFieldTypeChanged,
    NullableChanged,
    OpenApiParameterAdded,
    OpenApiParameterChanged,
    RequiredChanged,
    TypeChanged,
)
from driftguard.policy.models import PolicyDecision, PolicyMode, PolicyResult, Severity

# Type transitions that are considered widening (potentially safe)
WIDENING_TRANSITIONS: set[tuple[str, str]] = {
    ("integer", "number"),
    ("integer", "string"),
    ("number", "string"),
    ("boolean", "string"),
}


def evaluate(diff_result: DiffResult, mode: PolicyMode = PolicyMode.DEFAULT) -> PolicyResult:
    """Evaluate all diff events and produce policy decisions."""
    decisions = [_evaluate_event(event, mode) for event in diff_result.events]
    return PolicyResult(decisions=decisions)


def _evaluate_event(event: DiffEvent, mode: PolicyMode = PolicyMode.DEFAULT) -> PolicyDecision:
    """Evaluate a single diff event and return its policy decision."""
    decision = _evaluate_event_default(event)

    # Apply mode adjustments
    if mode == PolicyMode.STRICT:
        decision = _apply_strict(decision)
    elif mode == PolicyMode.LENIENT:
        decision = _apply_lenient(decision)
    elif mode == PolicyMode.BACKWARD_COMPATIBLE:
        decision = _apply_backward_compatible(decision)
    elif mode == PolicyMode.FORWARD_COMPATIBLE:
        decision = _apply_forward_compatible(decision)

    return decision


def _evaluate_event_default(event: DiffEvent) -> PolicyDecision:
    """Evaluate using default policy rules."""
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
        case ChangeCategory.DEFAULT_VALUE_CHANGED:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="Default value changed; may affect new records but existing data is unaffected",
            )
        case ChangeCategory.CONSTRAINT_CHANGED:
            return PolicyDecision(
                event=event,
                severity=Severity.WARNING,
                reason="Constraint changed; may affect data validation behavior",
            )
        case ChangeCategory.FOREIGN_KEY_CHANGED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="Foreign key relationship changed; referential integrity may be affected",
            )
        case ChangeCategory.PRIMARY_KEY_CHANGED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="Primary key changed; row identity and joins are affected",
            )
        case ChangeCategory.INDEX_CHANGED:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="Index changed; may affect query performance but not correctness",
            )
        # --- OpenAPI deep diff rules ---
        case ChangeCategory.OPENAPI_PATH_REMOVED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="API path removed; all consumers of this endpoint will fail",
            )
        case ChangeCategory.OPENAPI_PATH_ADDED:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="New API path added; backward compatible",
            )
        case ChangeCategory.OPENAPI_METHOD_REMOVED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="HTTP method removed; clients using this method will get 405",
            )
        case ChangeCategory.OPENAPI_METHOD_ADDED:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="New HTTP method added; backward compatible",
            )
        case ChangeCategory.OPENAPI_RESPONSE_STATUS_REMOVED:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason="Response status code removed; clients handling this status will break",
            )
        case ChangeCategory.OPENAPI_RESPONSE_STATUS_ADDED:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="New response status code added; existing clients unaffected",
            )
        case ChangeCategory.OPENAPI_PARAMETER_REMOVED:
            return PolicyDecision(
                event=event,
                severity=Severity.WARNING,
                reason="Parameter removed; clients sending this parameter may see unexpected behavior",
            )
        case ChangeCategory.OPENAPI_PARAMETER_ADDED:
            return _evaluate_parameter_added(event)
        case ChangeCategory.OPENAPI_PARAMETER_CHANGED:
            return _evaluate_parameter_changed(event)
        case ChangeCategory.OPENAPI_ENDPOINT_DEPRECATED:
            return PolicyDecision(
                event=event,
                severity=Severity.WARNING,
                reason="Endpoint marked as deprecated; plan migration before removal",
            )
        # --- Nested / JSONB diff rules ---
        case ChangeCategory.NESTED_FIELD_REMOVED:
            return _evaluate_nested_field_removed(event)
        case ChangeCategory.NESTED_FIELD_ADDED:
            return _evaluate_nested_field_added(event)
        case ChangeCategory.NESTED_FIELD_TYPE_CHANGED:
            return _evaluate_nested_type_changed(event)
        case ChangeCategory.NESTED_FIELD_REQUIRED_CHANGED:
            return _evaluate_nested_required_changed(event)
        case ChangeCategory.NESTED_FIELD_NULLABLE_CHANGED:
            return PolicyDecision(
                event=event,
                severity=Severity.WARNING,
                reason="Nested field nullable status changed; consumers without null handling may fail",
            )
        case ChangeCategory.NESTED_ENUM_VALUES_CHANGED:
            return _evaluate_nested_enum_changed(event)
        case _:
            return PolicyDecision(
                event=event,
                severity=Severity.INFO,
                reason="Unclassified change",
            )


def _apply_strict(decision: PolicyDecision) -> PolicyDecision:
    """Strict mode: promote warnings to breaking."""
    if decision.severity == Severity.WARNING:
        return PolicyDecision(
            event=decision.event,
            severity=Severity.BREAKING,
            reason=f"[strict] {decision.reason}",
        )
    if decision.severity == Severity.INFO:
        return PolicyDecision(
            event=decision.event,
            severity=Severity.WARNING,
            reason=f"[strict] {decision.reason}",
        )
    return decision


def _apply_lenient(decision: PolicyDecision) -> PolicyDecision:
    """Lenient mode: demote breaking to warning (except resource removal)."""
    if decision.severity == Severity.BREAKING and decision.event.category != ChangeCategory.RESOURCE_REMOVED:
        return PolicyDecision(
            event=decision.event,
            severity=Severity.WARNING,
            reason=f"[lenient] {decision.reason}",
        )
    return decision


def _apply_backward_compatible(decision: PolicyDecision) -> PolicyDecision:
    """Backward-compatible mode: only additions are safe, everything else is strict."""
    if (
        decision.event.category in (ChangeCategory.RESOURCE_ADDED, ChangeCategory.FIELD_ADDED)
        and decision.severity == Severity.INFO
    ):
        return decision
    if decision.severity == Severity.WARNING:
        return PolicyDecision(
            event=decision.event,
            severity=Severity.BREAKING,
            reason=f"[backward-compat] {decision.reason}",
        )
    return decision


def _apply_forward_compatible(decision: PolicyDecision) -> PolicyDecision:
    """Forward-compatible mode: only removals are safe, additions may be breaking."""
    if decision.event.category in (ChangeCategory.FIELD_ADDED,):
        return PolicyDecision(
            event=decision.event,
            severity=Severity.WARNING,
            reason=f"[forward-compat] {decision.reason}",
        )
    return decision


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


def _evaluate_parameter_added(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, OpenApiParameterAdded)
    if event.required:
        return PolicyDecision(
            event=event,
            severity=Severity.BREAKING,
            reason=f"Required {event.location} parameter '{event.param_name}' added; existing clients will fail",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.INFO,
        reason=f"Optional {event.location} parameter '{event.param_name}' added; backward compatible",
    )


def _evaluate_parameter_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, OpenApiParameterChanged)
    if "required: False -> True" in event.change_detail:
        return PolicyDecision(
            event=event,
            severity=Severity.BREAKING,
            reason=f"Parameter '{event.param_name}' became required; existing clients will fail",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.WARNING,
        reason=f"Parameter '{event.param_name}' changed ({event.change_detail})",
    )


# --- Nested / JSONB policy helpers ---


def _evaluate_nested_field_removed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, NestedFieldRemoved)
    if event.confidence >= 0.8:
        return PolicyDecision(
            event=event,
            severity=Severity.BREAKING,
            reason=f"Nested field '{event.path}' removed with high confidence ({event.confidence}); consumers will break",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.WARNING,
        reason=f"Nested field '{event.path}' removed with low confidence ({event.confidence}); may be intermittent",
    )


def _evaluate_nested_field_added(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, NestedFieldAdded)
    if event.required:
        if event.confidence >= 0.8:
            return PolicyDecision(
                event=event,
                severity=Severity.BREAKING,
                reason=f"Required nested field '{event.path}' added with high confidence; existing producers may not provide it",
            )
        return PolicyDecision(
            event=event,
            severity=Severity.WARNING,
            reason=f"Required nested field '{event.path}' added with low confidence ({event.confidence}); may be intermittent",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.INFO,
        reason=f"Optional nested field '{event.path}' added; backward compatible",
    )


def _evaluate_nested_type_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, NestedFieldTypeChanged)
    pair = (event.old_type, event.new_type)
    if pair in WIDENING_TRANSITIONS:
        return PolicyDecision(
            event=event,
            severity=Severity.WARNING,
            reason=f"Nested field '{event.path}' type widened from {event.old_type} to {event.new_type}",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.BREAKING,
        reason=f"Nested field '{event.path}' type changed from {event.old_type} to {event.new_type}; consumers will break",
    )


def _evaluate_nested_required_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, NestedFieldRequiredChanged)
    if event.old_required and not event.new_required:
        return PolicyDecision(
            event=event,
            severity=Severity.INFO,
            reason=f"Nested field '{event.path}' became optional; backward compatible",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.BREAKING,
        reason=f"Nested field '{event.path}' became required; existing data without this field will fail validation",
    )


def _evaluate_nested_enum_changed(event: DiffEvent) -> PolicyDecision:
    assert isinstance(event, NestedEnumValuesChanged)
    if event.removed_values:
        return PolicyDecision(
            event=event,
            severity=Severity.BREAKING,
            reason=f"Nested enum values removed from '{event.path}': {', '.join(event.removed_values)}; existing data may be invalid",
        )
    return PolicyDecision(
        event=event,
        severity=Severity.WARNING,
        reason=f"Nested enum values added to '{event.path}': {', '.join(event.added_values)}; strict consumers may not handle new values",
    )
