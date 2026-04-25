"""YAML schema collector.

Reads a YAML file and infers schema from the document structure.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldDef, ResourceSchema, SourceType


def _infer_type(value: object) -> str:
    """Infer normalized type from a Python value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


class YamlCollector(BaseCollector):
    """Collects schema from a YAML data file by inspecting its structure."""

    def __init__(self, file_path: str | Path, resource_name: str = "") -> None:
        self._file_path = Path(file_path)
        self._resource_name = resource_name or self._file_path.stem

    @property
    def name(self) -> str:
        return f"yaml:{self._resource_name}"

    def collect(self) -> list[ResourceSchema]:
        text = self._file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)

        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Array of objects — infer from first record
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            return []

        fields: list[FieldDef] = []
        for key, value in record.items():
            fields.append(
                FieldDef(
                    name=str(key),
                    field_type=_infer_type(value),
                    nullable=value is None,
                    required=True,
                )
            )

        return [
            ResourceSchema(
                name=self._resource_name,
                source_type=SourceType.JSON_SCHEMA,
                fields=fields,
            )
        ]
