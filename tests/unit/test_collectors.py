"""Tests for schema collectors."""

from pathlib import Path

from driftguard.collectors.csv_collector import CsvCollector
from driftguard.collectors.json_collector import JsonSchemaCollector, OpenApiCollector
from driftguard.schema.models import SourceType

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestJsonSchemaCollector:
    def test_collect(self) -> None:
        collector = JsonSchemaCollector(FIXTURES / "sample_schema.json", "users")
        resources = collector.collect()
        assert len(resources) == 1
        r = resources[0]
        assert r.name == "users"
        assert r.source_type == SourceType.JSON_SCHEMA
        assert r.field_names == {"id", "name", "email", "age", "status"}

    def test_required_fields(self) -> None:
        collector = JsonSchemaCollector(FIXTURES / "sample_schema.json")
        resources = collector.collect()
        r = resources[0]
        id_field = r.get_field("id")
        age_field = r.get_field("age")
        assert id_field is not None
        assert id_field.required is True
        assert age_field is not None
        assert age_field.required is False

    def test_nullable_from_type_array(self) -> None:
        collector = JsonSchemaCollector(FIXTURES / "sample_schema.json")
        r = collector.collect()[0]
        email = r.get_field("email")
        assert email is not None
        assert email.nullable is True

    def test_enum_values(self) -> None:
        collector = JsonSchemaCollector(FIXTURES / "sample_schema.json")
        r = collector.collect()[0]
        status = r.get_field("status")
        assert status is not None
        assert status.enum_values == ["active", "inactive", "banned"]

    def test_default_value(self) -> None:
        collector = JsonSchemaCollector(FIXTURES / "sample_schema.json")
        r = collector.collect()[0]
        age = r.get_field("age")
        assert age is not None
        assert age.default == 0

    def test_name_property(self) -> None:
        collector = JsonSchemaCollector(FIXTURES / "sample_schema.json", "my_schema")
        assert collector.name == "json-schema:my_schema"


class TestOpenApiCollector:
    def test_collect(self) -> None:
        collector = OpenApiCollector(FIXTURES / "sample_openapi.yaml")
        resources = collector.collect()
        assert len(resources) == 2
        names = {r.name for r in resources}
        assert names == {"User", "Order"}

    def test_user_schema(self) -> None:
        collector = OpenApiCollector(FIXTURES / "sample_openapi.yaml")
        resources = collector.collect()
        user = next(r for r in resources if r.name == "User")
        assert user.source_type == SourceType.OPENAPI
        assert user.field_names == {"id", "email", "role"}

        id_field = user.get_field("id")
        assert id_field is not None
        assert id_field.required is True
        assert id_field.field_type == "integer"

    def test_order_schema(self) -> None:
        collector = OpenApiCollector(FIXTURES / "sample_openapi.yaml")
        resources = collector.collect()
        order = next(r for r in resources if r.name == "Order")
        assert order.field_names == {"id", "total", "currency"}

        currency = order.get_field("currency")
        assert currency is not None
        assert currency.default == "USD"
        assert currency.required is False

    def test_enum_extraction(self) -> None:
        collector = OpenApiCollector(FIXTURES / "sample_openapi.yaml")
        resources = collector.collect()
        user = next(r for r in resources if r.name == "User")
        role = user.get_field("role")
        assert role is not None
        assert role.enum_values == ["admin", "user", "guest"]

    def test_name_property(self) -> None:
        collector = OpenApiCollector(FIXTURES / "sample_openapi.yaml")
        assert collector.name == "openapi:sample_openapi"


class TestCsvCollector:
    def test_collect(self) -> None:
        collector = CsvCollector(FIXTURES / "sample.csv", "users")
        resources = collector.collect()
        assert len(resources) == 1
        r = resources[0]
        assert r.name == "users"
        assert r.source_type == SourceType.CSV
        assert r.field_names == {"id", "name", "email", "age", "active"}

    def test_type_inference_integer(self) -> None:
        collector = CsvCollector(FIXTURES / "sample.csv")
        r = collector.collect()[0]
        id_field = r.get_field("id")
        assert id_field is not None
        assert id_field.field_type == "integer"

    def test_type_inference_string(self) -> None:
        collector = CsvCollector(FIXTURES / "sample.csv")
        r = collector.collect()[0]
        name_field = r.get_field("name")
        assert name_field is not None
        assert name_field.field_type == "string"

    def test_type_inference_boolean(self) -> None:
        collector = CsvCollector(FIXTURES / "sample.csv")
        r = collector.collect()[0]
        active = r.get_field("active")
        assert active is not None
        assert active.field_type == "boolean"

    def test_nullable_detection(self) -> None:
        collector = CsvCollector(FIXTURES / "sample.csv")
        r = collector.collect()[0]
        email = r.get_field("email")
        age = r.get_field("age")
        assert email is not None
        assert email.nullable is True  # row 3 has empty email
        assert age is not None
        assert age.nullable is True  # row 4 has empty age

    def test_name_property(self) -> None:
        collector = CsvCollector(FIXTURES / "sample.csv", "my_data")
        assert collector.name == "csv:my_data"

    def test_empty_csv(self, tmp_path: "object") -> None:

        p = Path(str(tmp_path)) / "empty.csv"
        p.write_text("", encoding="utf-8")
        collector = CsvCollector(p)
        resources = collector.collect()
        assert len(resources) == 1
        assert resources[0].fields == []
