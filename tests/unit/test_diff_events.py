"""Tests for diff event models."""

from driftguard.diff import (
    ChangeCategory,
    DiffEvent,
    DiffResult,
    EnumValuesChanged,
    FieldAdded,
    FieldRemoved,
    FieldRenamed,
    NullableChanged,
    RequiredChanged,
    ResourceAdded,
    ResourceRemoved,
    TypeChanged,
)


class TestDiffEvents:
    def test_resource_added(self) -> None:
        e = ResourceAdded(resource_name="payments", description="New resource: payments")
        assert e.category == ChangeCategory.RESOURCE_ADDED
        assert e.resource_name == "payments"

    def test_resource_removed(self) -> None:
        e = ResourceRemoved(resource_name="legacy_users", description="Removed resource: legacy_users")
        assert e.category == ChangeCategory.RESOURCE_REMOVED

    def test_field_added(self) -> None:
        e = FieldAdded(
            resource_name="users",
            description="Added field: phone",
            field_name="phone",
            field_type="string",
            required=False,
        )
        assert e.category == ChangeCategory.FIELD_ADDED
        assert e.field_name == "phone"
        assert e.required is False

    def test_field_added_required(self) -> None:
        e = FieldAdded(
            resource_name="users",
            description="Added required field: email",
            field_name="email",
            field_type="string",
            required=True,
        )
        assert e.required is True

    def test_field_removed(self) -> None:
        e = FieldRemoved(
            resource_name="users",
            description="Removed field: age",
            field_name="age",
            field_type="integer",
        )
        assert e.category == ChangeCategory.FIELD_REMOVED
        assert e.field_name == "age"

    def test_field_renamed(self) -> None:
        e = FieldRenamed(
            resource_name="users",
            description="Renamed field: name -> full_name",
            old_name="name",
            new_name="full_name",
            field_type="string",
        )
        assert e.category == ChangeCategory.FIELD_RENAMED
        assert e.old_name == "name"
        assert e.new_name == "full_name"

    def test_type_changed(self) -> None:
        e = TypeChanged(
            resource_name="orders",
            description="Type changed: amount (integer -> number)",
            field_name="amount",
            old_type="integer",
            new_type="number",
        )
        assert e.category == ChangeCategory.TYPE_CHANGED
        assert e.old_type == "integer"
        assert e.new_type == "number"

    def test_nullable_changed(self) -> None:
        e = NullableChanged(
            resource_name="users",
            description="Nullable changed: email (false -> true)",
            field_name="email",
            old_nullable=False,
            new_nullable=True,
        )
        assert e.category == ChangeCategory.NULLABLE_CHANGED
        assert e.old_nullable is False
        assert e.new_nullable is True

    def test_required_changed(self) -> None:
        e = RequiredChanged(
            resource_name="users",
            description="Required changed: phone (true -> false)",
            field_name="phone",
            old_required=True,
            new_required=False,
        )
        assert e.category == ChangeCategory.REQUIRED_CHANGED

    def test_enum_values_changed(self) -> None:
        e = EnumValuesChanged(
            resource_name="orders",
            description="Enum values changed: status",
            field_name="status",
            added_values=["cancelled"],
            removed_values=[],
        )
        assert e.category == ChangeCategory.ENUM_VALUES_CHANGED
        assert e.added_values == ["cancelled"]
        assert e.removed_values == []

    def test_serialization_roundtrip(self) -> None:
        e = TypeChanged(
            resource_name="orders",
            description="Type changed",
            field_name="amount",
            old_type="integer",
            new_type="string",
        )
        data = e.model_dump()
        restored = TypeChanged.model_validate(data)
        assert restored == e


class TestDiffResult:
    def _make_events(self) -> list[DiffEvent]:
        return [
            FieldRemoved(resource_name="users", description="Removed email", field_name="email", field_type="string"),
            FieldAdded(
                resource_name="users",
                description="Added phone",
                field_name="phone",
                field_type="string",
                required=False,
            ),
            TypeChanged(
                resource_name="orders",
                description="Type changed",
                field_name="amount",
                old_type="integer",
                new_type="string",
            ),
        ]

    def test_empty_result(self) -> None:
        r = DiffResult(baseline_name="v1", current_name="v2")
        assert r.has_changes is False
        assert r.event_count == 0

    def test_has_changes(self) -> None:
        r = DiffResult(baseline_name="v1", current_name="v2", events=self._make_events())
        assert r.has_changes is True
        assert r.event_count == 3

    def test_events_by_category(self) -> None:
        r = DiffResult(baseline_name="v1", current_name="v2", events=self._make_events())
        removed = r.events_by_category(ChangeCategory.FIELD_REMOVED)
        assert len(removed) == 1

    def test_events_for_resource(self) -> None:
        r = DiffResult(baseline_name="v1", current_name="v2", events=self._make_events())
        user_events = r.events_for_resource("users")
        assert len(user_events) == 2
        order_events = r.events_for_resource("orders")
        assert len(order_events) == 1
