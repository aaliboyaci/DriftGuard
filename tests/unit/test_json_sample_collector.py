"""Tests for JSON sample file collector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftguard.collectors.json_sample_collector import (
    JsonSampleCollector,
    JsonSampleCollectorError,
)
from driftguard.schema.nested_models import NestedFieldType


@pytest.fixture
def tmp_json_file(tmp_path: Path):
    """Factory fixture to create temporary JSON files."""

    def _create(filename: str, content: str) -> Path:
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return p

    return _create


class TestSingleJsonObject:
    def test_single_object_produces_resource(self, tmp_json_file) -> None:
        data = {"id": 1, "name": "Alice", "active": True}
        path = tmp_json_file("sample.json", json.dumps(data))

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 1
        assert result.name == "sample"
        assert "id" in result.field_paths
        assert "name" in result.field_paths
        assert "active" in result.field_paths

    def test_single_object_field_types(self, tmp_json_file) -> None:
        data = {"s": "hello", "i": 42, "f": 3.14, "b": True}
        path = tmp_json_file("types.json", json.dumps(data))

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.get_field("s").field_type == NestedFieldType.STRING
        assert result.get_field("i").field_type == NestedFieldType.INTEGER
        assert result.get_field("f").field_type == NestedFieldType.NUMBER
        assert result.get_field("b").field_type == NestedFieldType.BOOLEAN


class TestJsonArrayFile:
    def test_array_of_objects(self, tmp_json_file) -> None:
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]
        path = tmp_json_file("users.json", json.dumps(data))

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 3
        assert "id" in result.field_paths
        assert "name" in result.field_paths

    def test_array_with_nested_objects(self, tmp_json_file) -> None:
        data = [
            {"user": {"email": "a@b.com"}},
            {"user": {"email": "c@d.com"}},
        ]
        path = tmp_json_file("nested.json", json.dumps(data))

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 2
        assert "user.email" in result.field_paths

    def test_array_with_non_object_item_raises(self, tmp_json_file) -> None:
        data = [{"id": 1}, "not_an_object"]
        path = tmp_json_file("bad_array.json", json.dumps(data))

        collector = JsonSampleCollector(paths=[path])
        with pytest.raises(JsonSampleCollectorError, match="not an object"):
            collector.collect()


class TestNdjsonFile:
    def test_ndjson_parsing(self, tmp_json_file) -> None:
        lines = [
            '{"id": 1, "status": "active"}',
            '{"id": 2, "status": "inactive"}',
            '{"id": 3, "status": "active"}',
        ]
        path = tmp_json_file("events.ndjson", "\n".join(lines))

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 3
        assert "id" in result.field_paths
        assert "status" in result.field_paths

    def test_ndjson_skips_blank_lines(self, tmp_json_file) -> None:
        content = '{"a": 1}\n\n{"a": 2}\n\n'
        path = tmp_json_file("sparse.ndjson", content)

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 2

    def test_ndjson_with_partial_errors(self, tmp_json_file) -> None:
        content = '{"a": 1}\nINVALID\n{"a": 3}\n'
        path = tmp_json_file("partial.ndjson", content)

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        # Valid lines are still collected
        assert result.sample_count == 2


class TestMultipleFiles:
    def test_combines_samples_from_multiple_files(self, tmp_json_file) -> None:
        path1 = tmp_json_file("a.json", json.dumps([{"x": 1}, {"x": 2}]))
        path2 = tmp_json_file("b.json", json.dumps([{"x": 3}, {"x": 4}]))

        collector = JsonSampleCollector(paths=[path1, path2])
        result = collector.collect()

        assert result.sample_count == 4
        assert "x" in result.field_paths

    def test_custom_resource_name(self, tmp_json_file) -> None:
        path = tmp_json_file("data.json", json.dumps({"k": "v"}))

        collector = JsonSampleCollector(paths=[path], resource_name="my_resource")
        result = collector.collect()

        assert result.name == "my_resource"

    def test_source_contains_file_paths(self, tmp_json_file) -> None:
        path1 = tmp_json_file("one.json", json.dumps({"a": 1}))
        path2 = tmp_json_file("two.json", json.dumps({"b": 2}))

        collector = JsonSampleCollector(paths=[path1, path2])
        result = collector.collect()

        assert "one.json" in result.source
        assert "two.json" in result.source


class TestInvalidJson:
    def test_completely_invalid_json_raises(self, tmp_json_file) -> None:
        path = tmp_json_file("garbage.json", "this is not json at all")

        collector = JsonSampleCollector(paths=[path])
        with pytest.raises(JsonSampleCollectorError, match="Failed to parse"):
            collector.collect()

    def test_file_not_found_raises(self) -> None:
        collector = JsonSampleCollector(paths=[Path("/nonexistent/file.json")])
        with pytest.raises(JsonSampleCollectorError, match="File not found"):
            collector.collect()

    def test_non_object_top_level_raises(self, tmp_json_file) -> None:
        path = tmp_json_file("string.json", '"just a string"')

        collector = JsonSampleCollector(paths=[path])
        with pytest.raises(JsonSampleCollectorError, match="Expected JSON object"):
            collector.collect()


class TestEmptyFile:
    def test_empty_file_returns_zero_samples(self, tmp_json_file) -> None:
        path = tmp_json_file("empty.json", "")

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 0
        assert result.fields == []

    def test_whitespace_only_file_returns_zero_samples(self, tmp_json_file) -> None:
        path = tmp_json_file("whitespace.json", "   \n  \n  ")

        collector = JsonSampleCollector(paths=[path])
        result = collector.collect()

        assert result.sample_count == 0
        assert result.fields == []


class TestFileSizeLimit:
    def test_exceeds_default_limit_raises(self, tmp_json_file) -> None:
        # Create collector with tiny limit (1 MB)
        data = json.dumps({"x": "a" * 2_000_000})
        path = tmp_json_file("big.json", data)

        collector = JsonSampleCollector(paths=[path], max_file_size_mb=1)
        with pytest.raises(JsonSampleCollectorError, match="exceeds size limit"):
            collector.collect()

    def test_within_limit_succeeds(self, tmp_json_file) -> None:
        data = json.dumps({"x": "small"})
        path = tmp_json_file("small.json", data)

        collector = JsonSampleCollector(paths=[path], max_file_size_mb=1)
        result = collector.collect()

        assert result.sample_count == 1
