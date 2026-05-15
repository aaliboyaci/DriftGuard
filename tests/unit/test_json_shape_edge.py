"""Edge-case hardening tests for JSON shape inference engine.

Covers:
- Deep nesting beyond max_depth
- Very large arrays
- Heterogeneous arrays
- Sparse fields
- Map-like objects with many keys
- Empty and null nested objects
- Boolean vs int distinction
- Large string values
"""

from __future__ import annotations

from driftguard.inference.json_shape import InferenceConfig, infer_shape, infer_shape_single
from driftguard.schema.nested_models import NestedFieldType


class TestDeepNesting:
    """Test circular-like deep nesting beyond max_depth."""

    def test_15_levels_deep_with_max_depth_10(self) -> None:
        """Object 15 levels deep with max_depth=10 should not crash."""
        # Build a 15-level deep object: {"l0": {"l1": {"l2": ... {"l14": "leaf"}}}}
        sample: dict = {"leaf": "value"}
        for i in range(14, -1, -1):
            sample = {f"l{i}": sample}

        config = InferenceConfig(max_depth=10)
        result = infer_shape_single(sample, config=config)

        # Should not crash and should have fields up to depth 10
        assert result.sample_count == 1
        assert len(result.fields) > 0

        # Fields within max_depth should exist
        assert result.get_field("l0") is not None
        assert result.get_field("l0.l1") is not None

        # Fields beyond max_depth (10) should NOT exist
        # At depth 10 we've traversed l0.l1.l2...l9 (10 dots = depth 11)
        deep_path = ".".join(f"l{i}" for i in range(11))
        assert result.get_field(deep_path) is None

    def test_deep_nesting_no_crash_default_config(self) -> None:
        """15 levels deep with default max_depth=10 should not crash."""
        sample: dict = {"val": 42}
        for i in range(14, -1, -1):
            sample = {f"level{i}": sample}

        result = infer_shape_single(sample)
        assert result.sample_count == 1
        # No exception = pass


class TestLargeArray:
    """Test very large arrays don't cause per-item inflation."""

    def test_array_with_1000_items(self) -> None:
        """Array with 1000 items — verify only per-sample tracking."""
        items = [{"id": i, "value": f"item_{i}"} for i in range(1000)]
        sample = {"items": items}

        result = infer_shape_single(sample)

        # Should track paths not per-item but per-sample
        assert result.sample_count == 1
        assert result.get_field("items") is not None
        assert result.get_field("items").field_type == NestedFieldType.ARRAY
        assert result.get_field("items[].id") is not None
        assert result.get_field("items[].value") is not None
        # Occurrence count should be 1 (one sample)
        assert result.get_field("items[].id").occurrence_count == 1

    def test_large_array_across_samples(self) -> None:
        """Large arrays across multiple samples maintain correct sample count."""
        samples = [{"data": [{"x": i} for i in range(100)]} for _ in range(10)]
        result = infer_shape(samples)

        assert result.sample_count == 10
        assert result.get_field("data[].x") is not None
        assert result.get_field("data[].x").occurrence_count == 10


class TestHeterogeneousArray:
    """Test heterogeneous arrays with mixed types."""

    def test_mixed_type_array(self) -> None:
        """[{"a":1}, "string", 42, null] — only dict items get [] paths."""
        sample = {"items": [{"a": 1}, "string", 42, None]}

        result = infer_shape_single(sample)

        assert result.get_field("items") is not None
        assert result.get_field("items").field_type == NestedFieldType.ARRAY
        # Dict items should produce items[].a
        assert result.get_field("items[].a") is not None
        # Primitive items get items[] path
        assert result.get_field("items[]") is not None

    def test_all_primitives_array(self) -> None:
        """Array of only primitives should track items[] type."""
        sample = {"values": [1, 2, 3, 4, 5]}

        result = infer_shape_single(sample)

        assert result.get_field("values") is not None
        assert result.get_field("values[]") is not None
        assert result.get_field("values[]").field_type == NestedFieldType.INTEGER

    def test_mixed_primitives_in_array(self) -> None:
        """Array with mixed primitives (string + int)."""
        sample = {"mix": ["hello", 42, "world", 99]}

        result = infer_shape_single(sample)

        assert result.get_field("mix") is not None
        assert result.get_field("mix[]") is not None
        assert result.get_field("mix[]").field_type == NestedFieldType.MIXED


class TestSparseFields:
    """Test sparse fields with low occurrence confidence."""

    def test_field_in_2_of_100_samples(self) -> None:
        """100 samples where field appears in only 2 — confidence = 0.02."""
        samples = [{"id": i} for i in range(100)]
        # Add rare field to only 2 samples
        samples[10]["rare_field"] = "appears"
        samples[50]["rare_field"] = "appears"

        result = infer_shape(samples)

        rare = result.get_field("rare_field")
        assert rare is not None
        assert rare.occurrence_count == 2
        assert rare.confidence == 0.02
        assert rare.required is False

    def test_field_in_1_of_50_samples(self) -> None:
        """Field in 1 of 50 samples."""
        samples = [{"id": i} for i in range(50)]
        samples[25]["ultra_rare"] = "once"

        result = infer_shape(samples)

        field = result.get_field("ultra_rare")
        assert field is not None
        assert field.occurrence_count == 1
        assert field.confidence == 0.02
        assert field.required is False


class TestMapLikeObject:
    """Test objects with 100+ keys (map-like structures)."""

    def test_100_plus_keys(self) -> None:
        """Object with 100+ keys — still works, all fields recorded."""
        sample = {f"key_{i:03d}": f"value_{i}" for i in range(150)}

        result = infer_shape_single(sample)

        assert result.sample_count == 1
        # All 150 fields should be recorded
        assert len(result.fields) == 150
        assert result.get_field("key_000") is not None
        assert result.get_field("key_149") is not None

    def test_map_like_with_nested(self) -> None:
        """Map-like object where values are nested objects."""
        sample = {f"item_{i}": {"count": i, "active": i % 2 == 0} for i in range(50)}

        result = infer_shape_single(sample)

        # Should have paths for item_0.count, item_0.active, etc.
        assert result.get_field("item_0.count") is not None
        assert result.get_field("item_49.active") is not None


class TestEmptyNestedObject:
    """Test empty nested objects."""

    def test_empty_nested_object(self) -> None:
        """{"data": {}} should register data as object, no child fields."""
        sample = {"data": {}}

        result = infer_shape_single(sample)

        data_field = result.get_field("data")
        assert data_field is not None
        assert data_field.field_type == NestedFieldType.OBJECT
        # No child paths since object is empty
        child_paths = [f for f in result.fields if f.path.startswith("data.")]
        assert len(child_paths) == 0

    def test_empty_nested_across_samples(self) -> None:
        """Some samples have empty nested, others have populated nested."""
        samples = [
            {"data": {}},
            {"data": {"key": "value"}},
            {"data": {}},
        ]

        result = infer_shape(samples)

        assert result.get_field("data") is not None
        # key appears in 1 of 3 samples
        key_field = result.get_field("data.key")
        assert key_field is not None
        assert key_field.occurrence_count == 1


class TestNullNestedObject:
    """Test null nested objects."""

    def test_null_nested_object(self) -> None:
        """{"data": null} should be nullable."""
        sample = {"data": None}

        result = infer_shape_single(sample)

        data_field = result.get_field("data")
        assert data_field is not None
        assert data_field.nullable is True
        assert data_field.field_type == NestedFieldType.NULL

    def test_mixed_null_and_object(self) -> None:
        """Some samples have data as object, some as null."""
        samples = [
            {"data": {"x": 1}},
            {"data": None},
            {"data": {"x": 3}},
        ]

        result = infer_shape(samples)

        data_field = result.get_field("data")
        assert data_field is not None
        assert data_field.nullable is True


class TestBooleanVsInt:
    """Test that boolean values are never classified as integer."""

    def test_boolean_not_integer(self) -> None:
        """True/False should never be classified as integer."""
        samples = [
            {"flag": True},
            {"flag": False},
            {"flag": True},
        ]
        result = infer_shape(samples)

        field = result.get_field("flag")
        assert field is not None
        assert field.field_type == NestedFieldType.BOOLEAN
        assert field.field_type != NestedFieldType.INTEGER

    def test_boolean_mixed_with_int(self) -> None:
        """Boolean and integer together should be MIXED, not INTEGER."""
        samples = [
            {"val": True},
            {"val": 1},
            {"val": False},
            {"val": 0},
        ]
        result = infer_shape(samples)

        field = result.get_field("val")
        assert field is not None
        assert field.field_type == NestedFieldType.MIXED

    def test_boolean_in_nested(self) -> None:
        """Boolean in nested objects should remain boolean."""
        samples = [
            {"settings": {"enabled": True, "verbose": False}},
            {"settings": {"enabled": False, "verbose": True}},
        ]
        result = infer_shape(samples)

        assert result.get_field("settings.enabled").field_type == NestedFieldType.BOOLEAN
        assert result.get_field("settings.verbose").field_type == NestedFieldType.BOOLEAN


class TestLargeStringValue:
    """Test large string values don't break enum detection."""

    def test_10kb_string(self) -> None:
        """10KB string doesn't blow up enum detection."""
        large_value = "x" * 10240  # 10KB string
        samples = [
            {"content": large_value},
            {"content": "short"},
        ]

        result = infer_shape(samples)

        field = result.get_field("content")
        assert field is not None
        assert field.field_type == NestedFieldType.STRING
        # Should not crash — enum detection should still work
        # With only 2 distinct values, it might detect as enum or not
        # The key assertion is no crash

    def test_many_large_strings(self) -> None:
        """Multiple large strings don't cause memory issues."""
        samples = [{"text": "y" * 5000 + str(i)} for i in range(50)]

        result = infer_shape(samples)

        field = result.get_field("text")
        assert field is not None
        assert field.field_type == NestedFieldType.STRING
        # High cardinality large strings should not be enum candidates
        # (50 distinct values > default max_enum_values=20)

    def test_large_string_with_enum_detection_disabled(self) -> None:
        """Large strings with strict enum config."""
        large_value = "a" * 10240
        samples = [{"data": large_value}] * 30

        config = InferenceConfig(max_enum_values=5)
        result = infer_shape(samples, config=config)

        field = result.get_field("data")
        assert field is not None
        assert field.field_type == NestedFieldType.STRING
