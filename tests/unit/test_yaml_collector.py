"""Tests for YAML collector."""

from pathlib import Path

from driftguard.collectors.yaml_collector import YamlCollector, _infer_type


class TestInferType:
    def test_boolean(self) -> None:
        assert _infer_type(True) == "boolean"
        assert _infer_type(False) == "boolean"

    def test_integer(self) -> None:
        assert _infer_type(42) == "integer"

    def test_float(self) -> None:
        assert _infer_type(3.14) == "number"

    def test_list(self) -> None:
        assert _infer_type([1, 2]) == "array"

    def test_dict(self) -> None:
        assert _infer_type({"a": 1}) == "object"

    def test_string(self) -> None:
        assert _infer_type("hello") == "string"

    def test_none(self) -> None:
        assert _infer_type(None) == "string"


class TestYamlCollector:
    def test_dict_record(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        f.write_text("name: Alice\nage: 30\nactive: true\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        assert len(result) == 1
        assert result[0].name == "data"
        fields = {fd.name: fd for fd in result[0].fields}
        assert fields["name"].field_type == "string"
        assert fields["age"].field_type == "integer"
        assert fields["active"].field_type == "boolean"

    def test_list_of_dicts(self, tmp_path: Path) -> None:
        f = tmp_path / "users.yaml"
        f.write_text("- name: Alice\n  age: 30\n- name: Bob\n  age: 25\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        assert len(result) == 1
        assert len(result[0].fields) == 2

    def test_scalar_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "plain.yaml"
        f.write_text("just a string\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        assert result == []

    def test_empty_list_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("[]\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        assert result == []

    def test_custom_resource_name(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        f.write_text("key: value\n", encoding="utf-8")
        result = YamlCollector(f, resource_name="custom").collect()
        assert result[0].name == "custom"

    def test_name_property(self, tmp_path: Path) -> None:
        collector = YamlCollector(tmp_path / "test.yaml")
        assert collector.name == "yaml:test"

    def test_nullable_field(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        f.write_text("name: Alice\nnickname: null\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        fields = {fd.name: fd for fd in result[0].fields}
        assert fields["nickname"].nullable is True
        assert fields["name"].nullable is False

    def test_nested_object(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        f.write_text("user:\n  name: Alice\n  age: 30\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        fields = {fd.name: fd for fd in result[0].fields}
        assert fields["user"].field_type == "object"

    def test_array_field(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        f.write_text("tags:\n  - a\n  - b\nname: test\n", encoding="utf-8")
        result = YamlCollector(f).collect()
        fields = {fd.name: fd for fd in result[0].fields}
        assert fields["tags"].field_type == "array"
