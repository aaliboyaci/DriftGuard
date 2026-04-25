"""Tests for the diff engine."""

from driftguard.diff.engine import compute_diff
from driftguard.diff.events import ChangeCategory
from driftguard.schema.models import (
    ContractSnapshot,
    FieldConstraint,
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


class TestDiffEngineResources:
    def test_no_changes(self) -> None:
        s = _snap("v1", [_res("users", [_field("id", "integer")])])
        result = compute_diff(s, s)
        assert result.has_changes is False

    def test_resource_added(self) -> None:
        base = _snap("v1", [_res("users", [_field("id")])])
        curr = _snap("v2", [_res("users", [_field("id")]), _res("orders", [_field("id")])])
        result = compute_diff(base, curr)
        added = result.events_by_category(ChangeCategory.RESOURCE_ADDED)
        assert len(added) == 1
        assert added[0].resource_name == "orders"

    def test_resource_removed(self) -> None:
        base = _snap("v1", [_res("users", [_field("id")]), _res("legacy", [_field("id")])])
        curr = _snap("v2", [_res("users", [_field("id")])])
        result = compute_diff(base, curr)
        removed = result.events_by_category(ChangeCategory.RESOURCE_REMOVED)
        assert len(removed) == 1
        assert removed[0].resource_name == "legacy"

    def test_multiple_resources_added_and_removed(self) -> None:
        base = _snap("v1", [_res("a", [_field("id")]), _res("b", [_field("id")])])
        curr = _snap("v2", [_res("b", [_field("id")]), _res("c", [_field("id")]), _res("d", [_field("id")])])
        result = compute_diff(base, curr)
        assert len(result.events_by_category(ChangeCategory.RESOURCE_REMOVED)) == 1
        assert len(result.events_by_category(ChangeCategory.RESOURCE_ADDED)) == 2


class TestDiffEngineFields:
    def test_field_added(self) -> None:
        base = _snap("v1", [_res("users", [_field("id")])])
        curr = _snap("v2", [_res("users", [_field("id"), _field("email")])])
        result = compute_diff(base, curr)
        added = result.events_by_category(ChangeCategory.FIELD_ADDED)
        assert len(added) == 1
        assert added[0].resource_name == "users"

    def test_field_removed(self) -> None:
        base = _snap("v1", [_res("users", [_field("id"), _field("email")])])
        curr = _snap("v2", [_res("users", [_field("id")])])
        result = compute_diff(base, curr)
        removed = result.events_by_category(ChangeCategory.FIELD_REMOVED)
        assert len(removed) == 1

    def test_type_changed(self) -> None:
        base = _snap("v1", [_res("t", [_field("amount", "integer")])])
        curr = _snap("v2", [_res("t", [_field("amount", "string")])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.TYPE_CHANGED)
        assert len(changed) == 1

    def test_nullable_changed(self) -> None:
        base = _snap("v1", [_res("t", [_field("email", nullable=False)])])
        curr = _snap("v2", [_res("t", [_field("email", nullable=True)])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.NULLABLE_CHANGED)
        assert len(changed) == 1

    def test_required_changed(self) -> None:
        base = _snap("v1", [_res("t", [_field("name", required=True)])])
        curr = _snap("v2", [_res("t", [_field("name", required=False)])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.REQUIRED_CHANGED)
        assert len(changed) == 1

    def test_enum_values_added(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", enum_values=["a", "b"])])])
        curr = _snap("v2", [_res("t", [_field("status", enum_values=["a", "b", "c"])])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.ENUM_VALUES_CHANGED)
        assert len(changed) == 1

    def test_enum_values_removed(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", enum_values=["a", "b", "c"])])])
        curr = _snap("v2", [_res("t", [_field("status", enum_values=["a"])])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.ENUM_VALUES_CHANGED)
        assert len(changed) == 1

    def test_no_change_same_fields(self) -> None:
        fields = [_field("id", "integer"), _field("name", "string")]
        base = _snap("v1", [_res("t", fields)])
        curr = _snap("v2", [_res("t", fields)])
        result = compute_diff(base, curr)
        assert result.has_changes is False

    def test_multiple_field_changes(self) -> None:
        base = _snap(
            "v1",
            [
                _res(
                    "t",
                    [
                        _field("a", "integer"),
                        _field("b", "string", nullable=False),
                        _field("c", "string"),
                    ],
                )
            ],
        )
        curr = _snap(
            "v2",
            [
                _res(
                    "t",
                    [
                        _field("a", "string"),  # type changed
                        _field("b", "string", nullable=True),  # nullable changed
                        # c removed
                        _field("d", "boolean"),  # d added
                    ],
                )
            ],
        )
        result = compute_diff(base, curr)
        assert result.event_count == 4


class TestDiffEngineRename:
    def test_fuzzy_rename_detected(self) -> None:
        """email -> email_address with same type should be detected as rename."""
        base = _snap("v1", [_res("users", [_field("email", "string")])])
        curr = _snap("v2", [_res("users", [_field("email_address", "string")])])
        result = compute_diff(base, curr)
        renames = result.events_by_category(ChangeCategory.FIELD_RENAMED)
        assert len(renames) == 1
        assert renames[0].old_name == "email"
        assert renames[0].new_name == "email_address"
        # Should NOT also show up as remove + add
        assert len(result.events_by_category(ChangeCategory.FIELD_REMOVED)) == 0
        assert len(result.events_by_category(ChangeCategory.FIELD_ADDED)) == 0

    def test_no_rename_different_types(self) -> None:
        """Fields with different types should not be matched as rename."""
        base = _snap("v1", [_res("t", [_field("amount", "integer")])])
        curr = _snap("v2", [_res("t", [_field("amount_total", "string")])])
        result = compute_diff(base, curr)
        renames = result.events_by_category(ChangeCategory.FIELD_RENAMED)
        assert len(renames) == 0

    def test_no_rename_low_similarity(self) -> None:
        """Fields with completely different names should not be matched."""
        base = _snap("v1", [_res("t", [_field("foo", "string")])])
        curr = _snap("v2", [_res("t", [_field("xyz", "string")])])
        result = compute_diff(base, curr)
        renames = result.events_by_category(ChangeCategory.FIELD_RENAMED)
        assert len(renames) == 0


class TestDiffEngineNewEvents:
    def test_default_value_changed(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", default="active")])])
        curr = _snap("v2", [_res("t", [_field("status", default="pending")])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.DEFAULT_VALUE_CHANGED)
        assert len(changed) == 1

    def test_default_value_added(self) -> None:
        base = _snap("v1", [_res("t", [_field("name")])])
        curr = _snap("v2", [_res("t", [_field("name", default="unknown")])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.DEFAULT_VALUE_CHANGED)
        assert len(changed) == 1

    def test_default_value_removed(self) -> None:
        base = _snap("v1", [_res("t", [_field("name", default="test")])])
        curr = _snap("v2", [_res("t", [_field("name")])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.DEFAULT_VALUE_CHANGED)
        assert len(changed) == 1

    def test_constraint_pk_changed(self) -> None:
        base = _snap(
            "v1",
            [_res("t", [FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True))])],
        )
        curr = _snap(
            "v2",
            [_res("t", [FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=False))])],
        )
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.CONSTRAINT_CHANGED)
        assert len(changed) == 1

    def test_constraint_fk_changed(self) -> None:
        base = _snap(
            "v1",
            [
                _res(
                    "orders",
                    [
                        FieldDef(
                            name="user_id", field_type="integer", constraints=FieldConstraint(foreign_key="users.id")
                        )
                    ],
                )
            ],
        )
        curr = _snap(
            "v2",
            [_res("orders", [FieldDef(name="user_id", field_type="integer")])],
        )
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.FOREIGN_KEY_CHANGED)
        assert len(changed) == 1

    def test_constraint_max_length_changed(self) -> None:
        base = _snap(
            "v1",
            [_res("t", [FieldDef(name="name", field_type="string", constraints=FieldConstraint(max_length=50))])],
        )
        curr = _snap(
            "v2",
            [_res("t", [FieldDef(name="name", field_type="string", constraints=FieldConstraint(max_length=100))])],
        )
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.CONSTRAINT_CHANGED)
        assert len(changed) == 1

    def test_no_constraint_change(self) -> None:
        f = FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True))
        base = _snap("v1", [_res("t", [f])])
        curr = _snap("v2", [_res("t", [f])])
        result = compute_diff(base, curr)
        assert result.has_changes is False


class TestDiffEngineEdgeCases:
    def test_empty_snapshots(self) -> None:
        base = _snap("v1", [])
        curr = _snap("v2", [])
        result = compute_diff(base, curr)
        assert result.has_changes is False

    def test_empty_to_populated(self) -> None:
        base = _snap("v1", [])
        curr = _snap("v2", [_res("users", [_field("id")])])
        result = compute_diff(base, curr)
        assert len(result.events_by_category(ChangeCategory.RESOURCE_ADDED)) == 1

    def test_populated_to_empty(self) -> None:
        base = _snap("v1", [_res("users", [_field("id")])])
        curr = _snap("v2", [])
        result = compute_diff(base, curr)
        assert len(result.events_by_category(ChangeCategory.RESOURCE_REMOVED)) == 1

    def test_enum_added_where_none_existed(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", "string")])])
        curr = _snap("v2", [_res("t", [_field("status", "string", enum_values=["a", "b"])])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.ENUM_VALUES_CHANGED)
        assert len(changed) == 1

    def test_enum_removed_entirely(self) -> None:
        base = _snap("v1", [_res("t", [_field("status", "string", enum_values=["a", "b"])])])
        curr = _snap("v2", [_res("t", [_field("status", "string")])])
        result = compute_diff(base, curr)
        changed = result.events_by_category(ChangeCategory.ENUM_VALUES_CHANGED)
        assert len(changed) == 1
