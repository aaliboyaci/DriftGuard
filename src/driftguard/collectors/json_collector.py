"""JSON Schema and OpenAPI spec collector.

Extracts field definitions from:
- JSON Schema files (.json)
- OpenAPI/Swagger specs (.yaml/.json) - reads component schemas
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldDef, ResourceSchema, SourceType

# JSON Schema type to normalized type mapping
JSON_TYPE_MAP: dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
    "null": "null",
}


class JsonSchemaCollector(BaseCollector):
    """Collect schemas from JSON Schema files."""

    def __init__(self, path: str | Path, resource_name: str | None = None) -> None:
        self._path = Path(path)
        self._resource_name = resource_name or self._path.stem

    @property
    def name(self) -> str:
        return f"json-schema:{self._resource_name}"

    def collect(self) -> list[ResourceSchema]:
        text = self._path.read_text(encoding="utf-8")
        if self._path.suffix in (".yaml", ".yml"):
            schema = yaml.safe_load(text)
        else:
            schema = json.loads(text)

        fields = _extract_fields_from_schema(schema)
        return [
            ResourceSchema(
                name=self._resource_name,
                source_type=SourceType.JSON_SCHEMA,
                fields=fields,
            )
        ]


class OpenApiCollector(BaseCollector):
    """Collect schemas from OpenAPI specs (component schemas)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def name(self) -> str:
        return f"openapi:{self._path.stem}"

    def collect(self) -> list[ResourceSchema]:
        text = self._path.read_text(encoding="utf-8")
        if self._path.suffix in (".yaml", ".yml"):
            spec = yaml.safe_load(text)
        else:
            spec = json.loads(text)

        resources: list[ResourceSchema] = []
        schemas = _get_component_schemas(spec)

        for schema_name, schema_def in sorted(schemas.items()):
            fields = _extract_fields_from_schema(schema_def)
            resources.append(
                ResourceSchema(
                    name=schema_name,
                    source_type=SourceType.OPENAPI,
                    fields=fields,
                )
            )

        return resources


def _get_component_schemas(spec: dict[str, Any]) -> dict[str, Any]:
    """Extract component schemas from OpenAPI 3.x or Swagger 2.x spec."""
    # OpenAPI 3.x
    if "components" in spec and "schemas" in spec.get("components", {}):
        return spec["components"]["schemas"]
    # Swagger 2.x
    if "definitions" in spec:
        return spec["definitions"]
    return {}


def _extract_fields_from_schema(schema: dict[str, Any]) -> list[FieldDef]:
    """Extract FieldDef list from a JSON Schema object definition."""
    if schema.get("type") != "object" and "properties" not in schema:
        return []

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    fields: list[FieldDef] = []

    for prop_name, prop_def in properties.items():
        field_type = _resolve_type(prop_def)
        nullable = _is_nullable(prop_def)
        enum_values = prop_def.get("enum")

        fields.append(
            FieldDef(
                name=prop_name,
                field_type=field_type,
                nullable=nullable,
                required=prop_name in required_fields,
                default=prop_def.get("default"),
                description=prop_def.get("description"),
                enum_values=[str(v) for v in enum_values] if enum_values else None,
            )
        )

    return fields


def _resolve_type(prop_def: dict[str, Any]) -> str:
    """Resolve the normalized type from a JSON Schema property definition."""
    raw_type = prop_def.get("type", "object")
    if isinstance(raw_type, list):
        non_null = [t for t in raw_type if t != "null"]
        raw_type = non_null[0] if non_null else "null"
    return JSON_TYPE_MAP.get(raw_type, raw_type)


def _is_nullable(prop_def: dict[str, Any]) -> bool:
    """Check if a property is nullable."""
    raw_type = prop_def.get("type")
    if isinstance(raw_type, list) and "null" in raw_type:
        return True
    return prop_def.get("nullable", False)
