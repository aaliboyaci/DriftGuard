"""Tests for nested diff engine and nested policy rules."""

from __future__ import annotations

from driftguard.diff.events import (
    ChangeCategory,
    NestedEnumValuesChanged,
    NestedFieldAdded,
    NestedFieldNullableChanged,
    NestedFieldRemoved,
    NestedFieldRequiredChanged,
    NestedFieldTypeChanged,
)
from driftguard.diff.nested_engine import compute_nested_diff
from driftguard.policy.engine import evaluate
from driftguard.policy.models import Severity
from driftguard.schema.nested_models import (
    NestedContract,
    NestedField,
    NestedFieldType,
    NestedResource,
)


def _make_contract(name: str, resources: list[NestedResource]) -> NestedContract:
    return NestedContract(name=name, resources=resources)


def _make_resource(name: str, fields: list[NestedField]) -> NestedResource:
    return NestedResource(name=name, fields=fields)


def _make_field(
    path: str,
    field_type: NestedFieldType = NestedFieldType.STRING,
    required: bool = True,
    nullable: bool = False,
    confidence: float = 1.0,
    enum_candidates: list[str] | None = None,
) -> NestedField:
    return NestedField(
        path=path,
        field_type=field_type,
        required=required,
        nullable=nullable,
        confidence=confidence,
        enum_candidates=enum_candidates,
    )


class TestPathAddedRemoved:
    def test_field_removed_detected(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("user.email"), _make_field("user.name")])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("user.email")])],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        assert len(result.events) == 1
        event = result.events[0]
        assert isinstance(event, NestedFieldRemoved)
        assert event.category == ChangeCategory.NESTED_FIELD_REMOVED
        assert event.path == "user.name"
        assert event.resource_name == "payload"

    def test_field_added_detected(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("user.email")])],
        )
        current = _make_contract(
            "current",
            [
                _make_resource(
                    "payload",
                    [_make_field("user.email"), _make_field("user.phone", required=False)],
                )
            ],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        assert len(result.events) == 1
        event = result.events[0]
        assert isinstance(event, NestedFieldAdded)
        assert event.category == ChangeCategory.NESTED_FIELD_ADDED
        assert event.path == "user.phone"
        assert event.required is False

    def test_multiple_resources(self) -> None:
        baseline = _make_contract(
            "baseline",
            [
                _make_resource("events", [_make_field("id"), _make_field("ts")]),
                _make_resource("metrics", [_make_field("cpu"), _make_field("mem")]),
            ],
        )
        current = _make_contract(
            "current",
            [
                _make_resource("events", [_make_field("id")]),
                _make_resource("metrics", [_make_field("cpu"), _make_field("mem"), _make_field("disk")]),
            ],
        )
        result = compute_nested_diff(baseline, current)
        assert result.event_count == 2
        removed = result.events_by_category(ChangeCategory.NESTED_FIELD_REMOVED)
        added = result.events_by_category(ChangeCategory.NESTED_FIELD_ADDED)
        assert len(removed) == 1
        assert len(added) == 1
        assert removed[0].resource_name == "events"
        assert added[0].resource_name == "metrics"


class TestTypeChanged:
    def test_type_changed_detected(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("count", NestedFieldType.INTEGER)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("count", NestedFieldType.STRING)])],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        assert len(result.events) == 1
        event = result.events[0]
        assert isinstance(event, NestedFieldTypeChanged)
        assert event.old_type == "integer"
        assert event.new_type == "string"


class TestRequiredChanged:
    def test_required_changed_detected(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("tag", required=True)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("tag", required=False)])],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        assert len(result.events) == 1
        event = result.events[0]
        assert isinstance(event, NestedFieldRequiredChanged)
        assert event.old_required is True
        assert event.new_required is False


class TestNullableChanged:
    def test_nullable_changed_detected(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("value", nullable=False)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("value", nullable=True)])],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        event = result.events[0]
        assert isinstance(event, NestedFieldNullableChanged)
        assert event.old_nullable is False
        assert event.new_nullable is True


class TestEnumValuesChanged:
    def test_enum_values_added(self) -> None:
        baseline = _make_contract(
            "baseline",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle"])],
                )
            ],
        )
        current = _make_contract(
            "current",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle", "down"])],
                )
            ],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        event = result.events[0]
        assert isinstance(event, NestedEnumValuesChanged)
        assert event.added_values == ["down"]
        assert event.removed_values == []

    def test_enum_values_removed(self) -> None:
        baseline = _make_contract(
            "baseline",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle", "down"])],
                )
            ],
        )
        current = _make_contract(
            "current",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle"])],
                )
            ],
        )
        result = compute_nested_diff(baseline, current)
        assert result.has_changes
        event = result.events[0]
        assert isinstance(event, NestedEnumValuesChanged)
        assert event.removed_values == ["down"]
        assert event.added_values == []


class TestConfidencePassthrough:
    def test_confidence_on_removed(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("x", confidence=0.75)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [])],
        )
        result = compute_nested_diff(baseline, current)
        event = result.events[0]
        assert isinstance(event, NestedFieldRemoved)
        assert event.confidence == 0.75

    def test_confidence_on_added(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("y", confidence=0.9)])],
        )
        result = compute_nested_diff(baseline, current)
        event = result.events[0]
        assert isinstance(event, NestedFieldAdded)
        assert event.confidence == 0.9

    def test_confidence_on_type_changed(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("z", NestedFieldType.INTEGER, confidence=0.85)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("z", NestedFieldType.STRING, confidence=0.85)])],
        )
        result = compute_nested_diff(baseline, current)
        event = result.events[0]
        assert isinstance(event, NestedFieldTypeChanged)
        assert event.confidence == 0.85


class TestNestedPolicy:
    def test_high_confidence_removed_is_breaking(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("user.id", confidence=0.95)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.BREAKING

    def test_low_confidence_removed_is_warning(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("user.tag", confidence=0.5)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert not policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.WARNING

    def test_required_field_added_is_breaking(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("user.id", required=True, confidence=0.9)])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.BREAKING

    def test_optional_field_added_is_info(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("user.phone", required=False, confidence=0.9)])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert not policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.INFO

    def test_type_changed_breaking(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("age", NestedFieldType.STRING)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("age", NestedFieldType.INTEGER)])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.BREAKING

    def test_type_widened_is_warning(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("count", NestedFieldType.INTEGER)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("count", NestedFieldType.NUMBER)])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert not policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.WARNING

    def test_enum_removed_is_breaking(self) -> None:
        baseline = _make_contract(
            "baseline",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle", "down"])],
                )
            ],
        )
        current = _make_contract(
            "current",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle"])],
                )
            ],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.BREAKING

    def test_enum_added_is_warning(self) -> None:
        baseline = _make_contract(
            "baseline",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle"])],
                )
            ],
        )
        current = _make_contract(
            "current",
            [
                _make_resource(
                    "payload",
                    [_make_field("status", enum_candidates=["active", "idle", "down"])],
                )
            ],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert not policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.WARNING

    def test_nullable_changed_is_warning(self) -> None:
        baseline = _make_contract(
            "baseline",
            [_make_resource("payload", [_make_field("value", nullable=False)])],
        )
        current = _make_contract(
            "current",
            [_make_resource("payload", [_make_field("value", nullable=True)])],
        )
        diff_result = compute_nested_diff(baseline, current)
        policy_result = evaluate(diff_result)
        assert not policy_result.has_breaking
        assert policy_result.decisions[0].severity == Severity.WARNING
