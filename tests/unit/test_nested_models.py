"""Tests for nested/JSONB schema models."""

from __future__ import annotations

import json

from driftguard.schema.nested_models import (
    NestedContract,
    NestedField,
    NestedFieldType,
    NestedResource,
)


class TestNestedFieldPaths:
    def test_dot_path(self) -> None:
        f = NestedField(path="payload.user.email", field_type=NestedFieldType.STRING)
        assert f.depth == 3
        assert f.parent_path == "payload.user"
        assert f.field_name == "email"

    def test_array_path(self) -> None:
        f = NestedField(path="items[].sku", field_type=NestedFieldType.STRING)
        assert f.is_array_item is True
        assert f.field_name == "sku"
        assert f.parent_path == "items[]"

    def test_root_field(self) -> None:
        f = NestedField(path="id", field_type=NestedFieldType.INTEGER)
        assert f.depth == 1
        assert f.parent_path is None
        assert f.field_name == "id"

    def test_map_wildcard(self) -> None:
        f = NestedField(path="metadata.*", field_type=NestedFieldType.STRING)
        assert f.field_name == "*"
        assert f.parent_path == "metadata"

    def test_deep_nested(self) -> None:
        f = NestedField(path="a.b.c.d.e", field_type=NestedFieldType.OBJECT)
        assert f.depth == 5


class TestNestedFieldTypes:
    def test_all_types(self) -> None:
        types = [t.value for t in NestedFieldType]
        assert "string" in types
        assert "integer" in types
        assert "number" in types
        assert "boolean" in types
        assert "object" in types
        assert "array" in types
        assert "null" in types
        assert "mixed" in types

    def test_mixed_type(self) -> None:
        f = NestedField(path="value", field_type=NestedFieldType.MIXED)
        assert f.field_type == NestedFieldType.MIXED


class TestNestedFieldStatistics:
    def test_confidence_calculation(self) -> None:
        f = NestedField(
            path="user.phone",
            field_type=NestedFieldType.STRING,
            occurrence_count=34,
            sample_count=100,
            confidence=0.34,
        )
        assert f.confidence == 0.34
        assert f.required is True  # model default, not inferred here

    def test_full_confidence(self) -> None:
        f = NestedField(
            path="id",
            field_type=NestedFieldType.INTEGER,
            occurrence_count=100,
            sample_count=100,
            confidence=1.0,
        )
        assert f.confidence == 1.0

    def test_nullable(self) -> None:
        f = NestedField(path="x", field_type=NestedFieldType.STRING, nullable=True)
        assert f.nullable is True

    def test_enum_candidates(self) -> None:
        f = NestedField(
            path="status",
            field_type=NestedFieldType.STRING,
            enum_candidates=["active", "idle", "down"],
        )
        assert f.enum_candidates == ["active", "idle", "down"]

    def test_format_hint(self) -> None:
        f = NestedField(
            path="created_at",
            field_type=NestedFieldType.STRING,
            format_hint="datetime",
        )
        assert f.format_hint == "datetime"

    def test_examples_redacted_default(self) -> None:
        f = NestedField(path="x", field_type=NestedFieldType.STRING)
        assert f.examples_redacted is True


class TestNestedResource:
    def test_get_field(self) -> None:
        r = NestedResource(
            name="payload",
            fields=[
                NestedField(path="id", field_type=NestedFieldType.INTEGER),
                NestedField(path="name", field_type=NestedFieldType.STRING),
            ],
        )
        assert r.get_field("id") is not None
        assert r.get_field("id").field_type == NestedFieldType.INTEGER
        assert r.get_field("missing") is None

    def test_field_paths(self) -> None:
        r = NestedResource(
            name="data",
            fields=[
                NestedField(path="a.b", field_type=NestedFieldType.STRING),
                NestedField(path="a.c", field_type=NestedFieldType.INTEGER),
            ],
        )
        assert r.field_paths == {"a.b", "a.c"}

    def test_required_vs_optional(self) -> None:
        r = NestedResource(
            name="events",
            sample_count=100,
            fields=[
                NestedField(path="id", field_type=NestedFieldType.INTEGER, confidence=1.0),
                NestedField(path="tag", field_type=NestedFieldType.STRING, confidence=0.4),
                NestedField(path="ts", field_type=NestedFieldType.STRING, confidence=1.0),
            ],
        )
        assert len(r.required_fields) == 2
        assert len(r.optional_fields) == 1
        assert r.optional_fields[0].path == "tag"


class TestNestedContract:
    def test_get_resource(self) -> None:
        c = NestedContract(
            name="baseline",
            resources=[
                NestedResource(name="quality_plan", fields=[]),
                NestedResource(name="rule_config", fields=[]),
            ],
        )
        assert c.get_resource("quality_plan") is not None
        assert c.get_resource("missing") is None

    def test_resource_names(self) -> None:
        c = NestedContract(
            name="v1",
            resources=[
                NestedResource(name="a", fields=[]),
                NestedResource(name="b", fields=[]),
            ],
        )
        assert c.resource_names == {"a", "b"}


class TestNestedSerialization:
    def test_roundtrip(self) -> None:
        original = NestedContract(
            name="test",
            resources=[
                NestedResource(
                    name="payload",
                    source="events.data",
                    sample_count=50,
                    max_depth=3,
                    fields=[
                        NestedField(
                            path="machine.status",
                            field_type=NestedFieldType.STRING,
                            nullable=False,
                            required=True,
                            occurrence_count=50,
                            sample_count=50,
                            confidence=1.0,
                            enum_candidates=["active", "idle", "down"],
                            format_hint=None,
                        ),
                        NestedField(
                            path="items[].sku",
                            field_type=NestedFieldType.STRING,
                            occurrence_count=45,
                            sample_count=50,
                            confidence=0.9,
                        ),
                    ],
                )
            ],
        )
        # Serialize to JSON
        data = json.loads(original.model_dump_json())
        # Deserialize back
        restored = NestedContract.model_validate(data)
        assert restored.name == "test"
        assert len(restored.resources) == 1
        r = restored.resources[0]
        assert r.name == "payload"
        assert r.sample_count == 50
        assert len(r.fields) == 2
        f0 = r.fields[0]
        assert f0.path == "machine.status"
        assert f0.enum_candidates == ["active", "idle", "down"]
        f1 = r.fields[1]
        assert f1.path == "items[].sku"
        assert f1.confidence == 0.9

    def test_minimal_field(self) -> None:
        """Minimal field with only required attributes."""
        f = NestedField(path="x", field_type=NestedFieldType.STRING)
        data = json.loads(f.model_dump_json())
        restored = NestedField.model_validate(data)
        assert restored.path == "x"
        assert restored.field_type == NestedFieldType.STRING
        assert restored.confidence == 1.0
        assert restored.enum_candidates is None
