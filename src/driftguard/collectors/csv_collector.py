"""CSV file schema collector.

Infers field names and types from CSV file headers and sample data.
"""

from __future__ import annotations

import csv
from pathlib import Path

from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldDef, ResourceSchema, SourceType

MAX_SAMPLE_ROWS = 100


class CsvCollector(BaseCollector):
    """Collect schema from CSV files by reading headers and inferring types."""

    def __init__(self, path: str | Path, resource_name: str | None = None) -> None:
        self._path = Path(path)
        self._resource_name = resource_name or self._path.stem

    @property
    def name(self) -> str:
        return f"csv:{self._resource_name}"

    def collect(self) -> list[ResourceSchema]:
        with open(self._path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return [
                    ResourceSchema(
                        name=self._resource_name,
                        source_type=SourceType.CSV,
                        fields=[],
                    )
                ]

            headers = list(reader.fieldnames)
            # Sample rows for type inference
            sample_rows: list[dict[str, str | None]] = []
            for i, row in enumerate(reader):
                if i >= MAX_SAMPLE_ROWS:
                    break
                sample_rows.append(row)

        fields = [
            FieldDef(
                name=header,
                field_type=_infer_type(header, sample_rows),
                nullable=_has_nulls(header, sample_rows),
                required=True,
            )
            for header in headers
        ]

        return [
            ResourceSchema(
                name=self._resource_name,
                source_type=SourceType.CSV,
                fields=fields,
            )
        ]


def _infer_type(column: str, rows: list[dict[str, str | None]]) -> str:
    """Infer the type of a CSV column from sample values."""
    values = [row.get(column) for row in rows if row.get(column) not in (None, "")]
    if not values:
        return "string"

    # Try integer
    if all(_is_int(v) for v in values):
        return "integer"

    # Try number (float)
    if all(_is_number(v) for v in values):
        return "number"

    # Try boolean
    if all(_is_bool(v) for v in values):
        return "boolean"

    return "string"


def _is_int(value: str | None) -> bool:
    if value is None:
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_number(value: str | None) -> bool:
    if value is None:
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in ("true", "false", "0", "1", "yes", "no")


def _has_nulls(column: str, rows: list[dict[str, str | None]]) -> bool:
    """Check if a column has any null/empty values."""
    return any(row.get(column) in (None, "") for row in rows)
