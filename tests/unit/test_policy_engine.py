"""Tests for the policy engine."""

from driftguard.diff.engine import compute_diff
from driftguard.diff.events import (
    FieldRenamed,
)
from driftguard.policy.engine import evaluate
from driftguard.policy.models import Severity
from driftguard.schema.models import (
    ContractSnapshot,
    FieldDef,
    ResourceSchema,
    SourceType,
)


def _snap(name: str, resources: list[ResourceSchema]) -> ContractSnapshot:
    return ContractSnapshot(name=name, resources=resources)


def _res(name: str, fields: list[FieldDef]) -> ResourceSchema:
    return ResourceSchema(name=name, source_type=SourceType.POSTGRES, fields=fields)


def _field(name: str, field_type: str = "string", **kwargs) -> FieldDef:  # type: ignore[no-untyped-def]
    return FieldDef(name=name, field_type=field_type, **kwargs)


class TestPolicyEngineRules:
    def test_resource_removed_is_breaking(self) -> None:
        base = _snap("v1", [_res("users", [_field("id")])])
        curr = _snap("v2", [])
        result = evaluate(compute_diff(base, curr))
        assert result.has_breaking
        assert result.decisions[0].severity == Severity.BREAKING

    def test_resource_added_is_info(self) -> None:
        base = _snap("v1", [])
        curr = _snap("v2", [_res("users", [_field("id")])])
        result = evaluate(compute_diff(base, curr))
        assert not result.has_breaking
        assert result.decisions[0].severity == Severity.INFO

    def test_field_removed_is_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("id"), _field("email")])])
        curr = _snap("v2", [_res("t", [_field("id")])])
        result = evaluate(compute_diff(base, curr))
        assert result.has_breaking

    def test_optional_field_added_is_info(self) -> None:
        base = _snap("v1", [_res("t", [_field("id")])])
        curr = _snap("v2", [_res("t", [_field("id"), _field("phone", required=False)])])
        result = evaluate(compute_diff(base, curr))
        assert not result.has_breaking
        assert result.info_count == 1

    def test_required_field_added_is_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("id")])])
        curr = _snap("v2", [_res("t", [_field("id"), _field("email", required=True)])])
        result = evaluate(compute_diff(base, curr))
        assert result.has_breaking

    def test_type_narrowing_is_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("val", "string")])])
        curr = _snap("v2", [_res("t", [_field("val", "integer")])])
        result = evaluate(compute_diff(base, curr))
        assert result.has_breaking

    def test_type_widening_integer_to_number_is_warning(self) -> None:
        base = _snap("v1", [_res("t", [_field("amount", "integer")])])
        curr = _snap("v2", [_res("t", [_field("amount", "number")])])
        result = evaluate(compute_diff(base, curr))
        assert not result.has_breaking
        assert result.warning_count == 1

    def test_type_widening_integer_to_string_is_warning(self) -> None:
        base = _snap("v1", [_res("t", [_field("code", "integer")])])
        curr = _snap("v2", [_res("t", [_field("code", "string")])])
        result = evaluate(compute_diff(base, curr))
        assert result.warning_count == 1
        assert not result.has_breaking

    def test_nullable_false_to_true_is_warning(self) -> None:
        base = _snap("v1", [_res("t", [_field("email", nullable=False)])])
        curr = _snap("v2", [_res("t", [_field("email", nullable=True)])])
        result = evaluate(compute_diff(base, curr))
        assert result.warning_count == 1

    def test_nullable_true_to_false_is_warning(self) -> None:
        base = _snap("v1", [_res("t", [_field("email", nullable=True)])])
        curr = _snap("v2", [_res("t", [_field("email", nullable=False)])])
        result = evaluate(compute_diff(base, curr))
        assert result.warning_count == 1

    def test_required_to_optional_is_info(self) -> None:
        base = _snap("v1", [_res("t", [_field("name", required=True)])])
        curr = _snap("v2", [_res("t", [_field("name", required=False)])])
        result = evaluate(compute_diff(base, curr))
        assert result.info_count == 1
        assert not result.has_breaking

    def test_optional_to_required_is_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("name", required=False)])])
        curr = _snap("v2", [_res("t", [_field("name", required=True)])])
        result = evaluate(compute_diff(base, curr))
        assert result.has_breaking

    def test_enum_values_added_is_warning(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", enum_values=["a", "b"])])])
        curr = _snap("v2", [_res("t", [_field("status", enum_values=["a", "b", "c"])])])
        result = evaluate(compute_diff(base, curr))
        assert result.warning_count == 1

    def test_enum_values_removed_is_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", enum_values=["a", "b", "c"])])])
        curr = _snap("v2", [_res("t", [_field("status", enum_values=["a"])])])
        result = evaluate(compute_diff(base, curr))
        assert result.has_breaking

    def test_field_renamed_is_breaking(self) -> None:
        from driftguard.policy.engine import _evaluate_event

        event = FieldRenamed(
            resource_name="t",
            description="Renamed name -> full_name",
            old_name="name",
            new_name="full_name",
            field_type="string",
        )
        decision = _evaluate_event(event)
        assert decision.severity == Severity.BREAKING


class TestPolicyEngineExitCode:
    def test_exit_code_zero_no_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("id")])])
        curr = _snap("v2", [_res("t", [_field("id"), _field("phone", required=False)])])
        result = evaluate(compute_diff(base, curr))
        assert result.exit_code == 0

    def test_exit_code_one_with_breaking(self) -> None:
        base = _snap("v1", [_res("t", [_field("id"), _field("email")])])
        curr = _snap("v2", [_res("t", [_field("id")])])
        result = evaluate(compute_diff(base, curr))
        assert result.exit_code == 1

    def test_exit_code_zero_no_changes(self) -> None:
        s = _snap("v1", [_res("t", [_field("id")])])
        result = evaluate(compute_diff(s, s))
        assert result.exit_code == 0
