"""Nested / JSONB contract schema models.

Represents the inferred shape of nested JSON payloads (JSONB columns,
JSON API responses, event payloads). Each field is identified by a dot-path
with array notation: `payload.items[].sku`, `metadata.tags[]`.

Unlike flat FieldDef, nested fields carry sampling statistics:
occurrence_count, sample_count, confidence. This enables policy engines
to demote severity for low-confidence inferences.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NestedFieldType(str, Enum):
    """Normalized type for nested fields."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"
    MIXED = "mixed"


class NestedField(BaseModel):
    """A single field at a specific path within a nested document.

    Path format:
      - Dot-separated for object keys: `user.email`
      - Bracket notation for arrays: `items[].sku`
      - Wildcard for map keys: `metadata.*`
    """

    path: str = Field(description="Full dot-path: payload.items[].sku")
    field_type: NestedFieldType
    nullable: bool = False
    required: bool = True
    occurrence_count: int = Field(default=0, description="How many samples contained this path")
    sample_count: int = Field(default=0, description="Total samples analyzed")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="occurrence_count / sample_count — 1.0 means present in all samples",
    )
    enum_candidates: list[str] | None = Field(
        default=None,
        description="Distinct values if cardinality is low enough to suggest an enum",
    )
    format_hint: str | None = Field(
        default=None,
        description="Detected format: date, datetime, uuid, email, uri",
    )
    examples_redacted: bool = Field(
        default=True,
        description="Whether raw example values are stripped (for PII safety)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def depth(self) -> int:
        """Nesting depth based on path segments."""
        return self.path.count(".") + 1

    @property
    def parent_path(self) -> str | None:
        """Parent field path, or None for root-level fields."""
        if "." not in self.path:
            return None
        return self.path.rsplit(".", 1)[0]

    @property
    def field_name(self) -> str:
        """Leaf field name without parent path."""
        return self.path.rsplit(".", 1)[-1]

    @property
    def is_array_item(self) -> bool:
        """Whether this path represents array item fields."""
        return "[]" in self.path


class NestedResource(BaseModel):
    """A single nested contract resource (one JSONB column, one event topic, one payload type)."""

    name: str = Field(description="Resource identifier: column name, topic, payload type")
    source: str = Field(default="", description="Where this came from: table.column, file path, etc.")
    fields: list[NestedField] = Field(default_factory=list)
    sample_count: int = Field(default=0, description="Total samples used for inference")
    max_depth: int = Field(default=0, description="Maximum nesting depth encountered")

    def get_field(self, path: str) -> NestedField | None:
        """Look up a field by full path."""
        for f in self.fields:
            if f.path == path:
                return f
        return None

    @property
    def field_paths(self) -> set[str]:
        """All field paths in this resource."""
        return {f.path for f in self.fields}

    @property
    def required_fields(self) -> list[NestedField]:
        """Fields present in all samples (confidence == 1.0)."""
        return [f for f in self.fields if f.confidence == 1.0]

    @property
    def optional_fields(self) -> list[NestedField]:
        """Fields not present in all samples."""
        return [f for f in self.fields if f.confidence < 1.0]


class NestedContract(BaseModel):
    """Collection of nested resources forming a contract snapshot.

    Analogous to ContractSnapshot but for inferred nested schemas.
    """

    name: str = Field(description="Contract identifier: baseline, current, v1.0")
    resources: list[NestedResource] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_resource(self, name: str) -> NestedResource | None:
        for r in self.resources:
            if r.name == name:
                return r
        return None

    @property
    def resource_names(self) -> set[str]:
        return {r.name for r in self.resources}
