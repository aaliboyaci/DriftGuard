"""Tests for JSON shape inference engine."""

from __future__ import annotations

from driftguard.inference.json_shape import InferenceConfig, infer_shape, infer_shape_single
from driftguard.schema.nested_models import NestedFieldType


class TestSingleSample:
    def test_flat_object(self) -> None:
        sample = {"id": 1, "name": "Alice", "active": True}
        result = infer_shape_single(sample)
        assert result.sample_count == 1
        paths = result.field_paths
        assert "id" in paths
        assert "name" in paths
        assert "active" in paths

    def test_types(self) -> None:
        sample = {"s": "hello", "i": 42, "f": 3.14, "b": True, "n": None}
        result = infer_shape_single(sample)
        assert result.get_field("s").field_type == NestedFieldType.STRING
        assert result.get_field("i").field_type == NestedFieldType.INTEGER
        assert result.get_field("f").field_type == NestedFieldType.NUMBER
        assert result.get_field("b").field_type == NestedFieldType.BOOLEAN
        assert result.get_field("n").field_type == NestedFieldType.NULL

    def test_nested_object(self) -> None:
        sample = {"user": {"name": "Alice", "address": {"city": "Istanbul"}}}
        result = infer_shape_single(sample)
        assert result.get_field("user") is not None
        assert result.get_field("user").field_type == NestedFieldType.OBJECT
        assert result.get_field("user.name") is not None
        assert result.get_field("user.address") is not None
        assert result.get_field("user.address.city") is not None

    def test_array_of_objects(self) -> None:
        sample = {"items": [{"sku": "A1", "qty": 5}, {"sku": "B2", "qty": 3}]}
        result = infer_shape_single(sample)
        assert result.get_field("items") is not None
        assert result.get_field("items").field_type == NestedFieldType.ARRAY
        assert result.get_field("items[].sku") is not None
        assert result.get_field("items[].qty") is not None

    def test_primitive_array(self) -> None:
        sample = {"tags": ["a", "b", "c"]}
        result = infer_shape_single(sample)
        assert result.get_field("tags") is not None
        assert result.get_field("tags[]") is not None
        assert result.get_field("tags[]").field_type == NestedFieldType.STRING

    def test_empty_array(self) -> None:
        sample = {"items": []}
        result = infer_shape_single(sample)
        assert result.get_field("items") is not None
        assert result.get_field("items").field_type == NestedFieldType.ARRAY
        # No items[] path since no elements to inspect
        assert result.get_field("items[]") is None

    def test_null_value(self) -> None:
        sample = {"name": "Alice", "phone": None}
        result = infer_shape_single(sample)
        assert result.get_field("phone").nullable is True
        assert result.get_field("name").nullable is False

    def test_max_depth(self) -> None:
        sample = {"a": {"b": {"c": {"d": {"e": {"f": "deep"}}}}}}
        config = InferenceConfig(max_depth=3)
        result = infer_shape_single(sample, config=config)
        # Should stop at depth 3
        assert result.get_field("a.b.c") is not None
        assert result.get_field("a.b.c.d") is None


class TestMultipleSamples:
    def test_occurrence_count(self) -> None:
        samples = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3},  # name missing
        ]
        result = infer_shape(samples)
        assert result.get_field("id").occurrence_count == 3
        assert result.get_field("id").confidence == 1.0
        assert result.get_field("name").occurrence_count == 2
        assert abs(result.get_field("name").confidence - 0.6667) < 0.01

    def test_required_vs_optional(self) -> None:
        samples = [
            {"id": 1, "tag": "a"},
            {"id": 2, "tag": "b"},
            {"id": 3, "tag": "c"},
        ]
        result = infer_shape(samples)
        assert result.get_field("id").required is True
        assert result.get_field("tag").required is True

        samples2 = [
            {"id": 1, "tag": "a"},
            {"id": 2},
            {"id": 3},
        ]
        result2 = infer_shape(samples2)
        assert result2.get_field("id").required is True
        assert result2.get_field("tag").required is False

    def test_mixed_types(self) -> None:
        samples = [
            {"value": "hello"},
            {"value": 42},
            {"value": True},
        ]
        result = infer_shape(samples)
        assert result.get_field("value").field_type == NestedFieldType.MIXED

    def test_integer_number_merge(self) -> None:
        samples = [
            {"amount": 100},
            {"amount": 99.5},
        ]
        result = infer_shape(samples)
        assert result.get_field("amount").field_type == NestedFieldType.NUMBER

    def test_sample_count(self) -> None:
        samples = [{"x": i} for i in range(10)]
        result = infer_shape(samples, resource_name="test")
        assert result.sample_count == 10
        assert result.name == "test"


class TestEnumDetection:
    def test_low_cardinality_enum(self) -> None:
        samples = [{"status": "active"}] * 30 + [{"status": "idle"}] * 30 + [{"status": "down"}] * 30
        result = infer_shape(samples)
        f = result.get_field("status")
        assert f.enum_candidates is not None
        assert set(f.enum_candidates) == {"active", "idle", "down"}

    def test_high_cardinality_no_enum(self) -> None:
        samples = [{"name": f"user_{i}"} for i in range(50)]
        config = InferenceConfig(max_enum_values=20)
        result = infer_shape(samples, config=config)
        f = result.get_field("name")
        assert f.enum_candidates is None

    def test_single_value_no_enum(self) -> None:
        samples = [{"x": "only"}]
        result = infer_shape(samples)
        # Only 1 sample — shouldn't crash
        result.get_field("x")


class TestFormatDetection:
    def test_uuid_format(self) -> None:
        samples = [
            {"id": "550e8400-e29b-41d4-a716-446655440000"},
            {"id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"},
        ]
        result = infer_shape(samples)
        assert result.get_field("id").format_hint == "uuid"

    def test_email_format(self) -> None:
        samples = [
            {"email": "alice@example.com"},
            {"email": "bob@test.org"},
        ]
        result = infer_shape(samples)
        assert result.get_field("email").format_hint == "email"

    def test_datetime_format(self) -> None:
        samples = [
            {"ts": "2024-01-15T10:30:00Z"},
            {"ts": "2024-02-20T14:00:00Z"},
        ]
        result = infer_shape(samples)
        assert result.get_field("ts").format_hint == "datetime"

    def test_date_format(self) -> None:
        samples = [
            {"date": "2024-01-15"},
            {"date": "2024-02-20"},
        ]
        result = infer_shape(samples)
        assert result.get_field("date").format_hint == "date"

    def test_no_format_for_random_strings(self) -> None:
        samples = [
            {"name": "Alice"},
            {"name": "Bob"},
        ]
        result = infer_shape(samples)
        assert result.get_field("name").format_hint is None


class TestNestedArrays:
    def test_nested_array_objects(self) -> None:
        samples = [
            {"orders": [{"id": 1, "items": [{"sku": "A"}]}, {"id": 2, "items": [{"sku": "B"}]}]},
        ]
        result = infer_shape_single(samples[0])
        assert result.get_field("orders") is not None
        assert result.get_field("orders[].id") is not None
        assert result.get_field("orders[].items") is not None
        assert result.get_field("orders[].items[].sku") is not None

    def test_array_confidence_across_samples(self) -> None:
        samples = [
            {"items": [{"sku": "A", "qty": 1}]},
            {"items": [{"sku": "B"}]},  # qty missing in this item
        ]
        result = infer_shape(samples)
        # Both samples have items[].sku
        assert result.get_field("items[].sku").confidence == 1.0


class TestEdgeCases:
    def test_empty_samples(self) -> None:
        result = infer_shape([])
        assert result.sample_count == 0
        assert result.fields == []

    def test_empty_object(self) -> None:
        result = infer_shape([{}])
        assert result.sample_count == 1
        assert result.fields == []

    def test_resource_name_and_source(self) -> None:
        result = infer_shape([{"x": 1}], resource_name="data", source="events.payload")
        assert result.name == "data"
        assert result.source == "events.payload"

    def test_max_samples_limit(self) -> None:
        samples = [{"x": i} for i in range(100)]
        config = InferenceConfig(max_samples=10)
        result = infer_shape(samples, config=config)
        assert result.sample_count == 10

    def test_boolean_not_integer(self) -> None:
        """Python bool is subclass of int; ensure correct detection."""
        samples = [{"flag": True}, {"flag": False}]
        result = infer_shape(samples)
        assert result.get_field("flag").field_type == NestedFieldType.BOOLEAN
