"""Tests for core schema models."""

from datetime import UTC, datetime

from driftguard.schema import (
    ContractSnapshot,
    FieldConstraint,
    FieldDef,
    ResourceSchema,
    SourceType,
)


def _make_field(name: str = "id", field_type: str = "integer", **kwargs) -> FieldDef:  # type: ignore[no-untyped-def]
    return FieldDef(name=name, field_type=field_type, **kwargs)


def _make_resource(name: str = "users", fields: list[FieldDef] | None = None) -> ResourceSchema:
    return ResourceSchema(
        name=name,
        source_type=SourceType.POSTGRES,
        fields=fields or [_make_field()],
    )


class TestFieldDef:
    def test_create_minimal(self) -> None:
        f = FieldDef(name="email", field_type="string")
        assert f.name == "email"
        assert f.field_type == "string"
        assert f.nullable is False
        assert f.required is True
        assert f.default is None
        assert f.enum_values is None

    def test_create_with_all_fields(self) -> None:
        f = FieldDef(
            name="status",
            field_type="string",
            nullable=True,
            required=False,
            default="active",
            description="User status",
            enum_values=["active", "inactive", "banned"],
            constraints=FieldConstraint(unique=True),
            metadata={"source_column": "user_status"},
        )
        assert f.nullable is True
        assert f.required is False
        assert f.default == "active"
        assert f.enum_values == ["active", "inactive", "banned"]
        assert f.constraints is not None
        assert f.constraints.unique is True
        assert f.metadata["source_column"] == "user_status"

    def test_serialization_roundtrip(self) -> None:
        f = _make_field(name="amount", field_type="number", nullable=True)
        data = f.model_dump()
        restored = FieldDef.model_validate(data)
        assert restored == f

    def test_json_roundtrip(self) -> None:
        f = _make_field(enum_values=["a", "b"])
        json_str = f.model_dump_json()
        restored = FieldDef.model_validate_json(json_str)
        assert restored == f


class TestFieldConstraint:
    def test_defaults(self) -> None:
        c = FieldConstraint()
        assert c.primary_key is False
        assert c.unique is False
        assert c.foreign_key is None

    def test_primary_key(self) -> None:
        c = FieldConstraint(primary_key=True)
        assert c.primary_key is True

    def test_foreign_key(self) -> None:
        c = FieldConstraint(foreign_key="orders.id")
        assert c.foreign_key == "orders.id"


class TestResourceSchema:
    def test_create(self) -> None:
        r = _make_resource("customers", [_make_field("id"), _make_field("name", "string")])
        assert r.name == "customers"
        assert r.source_type == SourceType.POSTGRES
        assert len(r.fields) == 2

    def test_field_names(self) -> None:
        r = _make_resource("t", [_make_field("a"), _make_field("b"), _make_field("c")])
        assert r.field_names == {"a", "b", "c"}

    def test_get_field_found(self) -> None:
        r = _make_resource("t", [_make_field("email", "string")])
        f = r.get_field("email")
        assert f is not None
        assert f.field_type == "string"

    def test_get_field_not_found(self) -> None:
        r = _make_resource("t", [_make_field("id")])
        assert r.get_field("nonexistent") is None

    def test_all_source_types(self) -> None:
        for st in SourceType:
            r = ResourceSchema(name="test", source_type=st)
            assert r.source_type == st

    def test_serialization_roundtrip(self) -> None:
        r = _make_resource("orders", [_make_field("id"), _make_field("total", "number")])
        data = r.model_dump()
        restored = ResourceSchema.model_validate(data)
        assert restored == r


class TestContractSnapshot:
    def test_create_empty(self) -> None:
        s = ContractSnapshot(name="baseline")
        assert s.name == "baseline"
        assert len(s.resources) == 0
        assert isinstance(s.created_at, datetime)

    def test_create_with_resources(self) -> None:
        s = ContractSnapshot(
            name="v1.0",
            resources=[_make_resource("users"), _make_resource("orders")],
        )
        assert s.resource_names == {"users", "orders"}

    def test_get_resource_found(self) -> None:
        s = ContractSnapshot(name="test", resources=[_make_resource("users")])
        r = s.get_resource("users")
        assert r is not None
        assert r.name == "users"

    def test_get_resource_not_found(self) -> None:
        s = ContractSnapshot(name="test", resources=[_make_resource("users")])
        assert s.get_resource("orders") is None

    def test_created_at_is_utc(self) -> None:
        s = ContractSnapshot(name="test")
        assert s.created_at.tzinfo == UTC

    def test_snapshot_v2_metadata(self) -> None:
        s = ContractSnapshot(
            name="v2-test",
            created_by="ci-bot",
            git_commit_sha="abc123def",
            branch_name="main",
            source_hash="sha256:deadbeef",
            collector_version="0.1.0",
            environment="production",
            tags=["nightly", "full-scan"],
            description="Nightly full schema scan",
        )
        assert s.schema_version == 1
        assert s.created_by == "ci-bot"
        assert s.git_commit_sha == "abc123def"
        assert s.branch_name == "main"
        assert s.source_hash == "sha256:deadbeef"
        assert s.collector_version == "0.1.0"
        assert s.environment == "production"
        assert s.tags == ["nightly", "full-scan"]
        assert s.description == "Nightly full schema scan"

    def test_snapshot_v2_defaults(self) -> None:
        s = ContractSnapshot(name="minimal")
        assert s.schema_version == 1
        assert s.created_by is None
        assert s.git_commit_sha is None
        assert s.tags == []
        assert s.description is None

    def test_snapshot_backward_compat(self) -> None:
        """Old snapshots without v2 fields should still deserialize."""
        old_data = {
            "name": "old-snapshot",
            "resources": [],
            "metadata": {"version": "0.1.0"},
        }
        s = ContractSnapshot.model_validate(old_data)
        assert s.name == "old-snapshot"
        assert s.schema_version == 1
        assert s.created_by is None
        assert s.tags == []

    def test_json_roundtrip(self) -> None:
        s = ContractSnapshot(
            name="full",
            resources=[
                _make_resource("users", [_make_field("id"), _make_field("email", "string")]),
                _make_resource("orders", [_make_field("id"), _make_field("total", "number")]),
            ],
            metadata={"env": "production"},
        )
        json_str = s.model_dump_json()
        restored = ContractSnapshot.model_validate_json(json_str)
        assert restored.name == s.name
        assert restored.resource_names == s.resource_names
        assert restored.metadata == s.metadata
