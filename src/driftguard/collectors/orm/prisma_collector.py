"""Prisma schema file collector.

Parses schema.prisma files using regex patterns.
Extracts model definitions, fields, types, constraints, and defaults.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from driftguard.collectors.orm.base import BaseOrmCollector
from driftguard.schema.models import FieldConstraint, FieldDef, ResourceSchema, SourceType

# Prisma type to normalized type mapping
PRISMA_TYPE_MAP: dict[str, str] = {
    "String": "string",
    "Int": "integer",
    "Float": "number",
    "Boolean": "boolean",
    "DateTime": "string(datetime)",
    "Json": "object",
    "BigInt": "integer",
    "Decimal": "number",
    "Bytes": "string",
}

# Pattern to match model blocks
_MODEL_PATTERN = re.compile(
    r"""model\s+(\w+)\s*\{([^}]*)\}""",
    re.MULTILINE | re.DOTALL,
)

# Pattern to match a field line: fieldName Type? @attributes
_FIELD_PATTERN = re.compile(
    r"""^[ \t]+(\w+)[ \t]+([\w]+)(\?)?(\[\])?[ \t]*(.*)$""",
    re.MULTILINE,
)


class PrismaCollector(BaseOrmCollector):
    """Collect schemas from Prisma schema files."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def name(self) -> str:
        return "prisma"

    def collect(self) -> list[ResourceSchema]:
        content = self._path.read_text(encoding="utf-8")
        resources: list[ResourceSchema] = []

        for match in _MODEL_PATTERN.finditer(content):
            model_name = match.group(1)
            model_body = match.group(2)
            fields = self._parse_fields(model_body)

            resources.append(
                ResourceSchema(
                    name=model_name,
                    source_type=SourceType.PRISMA,
                    fields=fields,
                    metadata={"file": str(self._path)},
                )
            )

        return resources

    def _parse_fields(self, model_body: str) -> list[FieldDef]:
        """Parse all field definitions from a model body."""
        fields: list[FieldDef] = []

        for match in _FIELD_PATTERN.finditer(model_body):
            field_name = match.group(1)
            field_type_raw = match.group(2)
            is_optional = match.group(3) == "?"
            is_array = match.group(4) == "[]"
            attributes = match.group(5).strip()

            # Skip relation fields (types that are other model names not in type map)
            # and array relations like Post[]
            if is_array:
                continue

            # Check if this is a known Prisma scalar type
            normalized_type = PRISMA_TYPE_MAP.get(field_type_raw)
            if normalized_type is None:
                # This is a relation field (references another model)
                # Only include if it has @relation attribute for FK extraction
                if "@relation" not in attributes:
                    continue
                # Still skip - relation fields are not actual columns
                continue

            nullable = is_optional
            default = self._extract_default(attributes)
            constraints = self._extract_constraints(attributes)

            fields.append(
                FieldDef(
                    name=field_name,
                    field_type=normalized_type,
                    nullable=nullable,
                    required=not nullable,
                    default=default,
                    constraints=constraints,
                )
            )

        return fields

    def _extract_default(self, attributes: str) -> Any:
        """Extract @default(...) value, handling nested parentheses."""
        # Find @default( and then match balanced parens
        idx = attributes.find("@default(")
        if idx == -1:
            return None

        # Start after '@default('
        start = idx + len("@default(")
        depth = 1
        pos = start
        while pos < len(attributes) and depth > 0:
            if attributes[pos] == "(":
                depth += 1
            elif attributes[pos] == ")":
                depth -= 1
            pos += 1

        value = attributes[start : pos - 1]

        # Handle common Prisma default functions
        if value in ("autoincrement()", "now()", "uuid()", "cuid()"):
            return value

        # Handle boolean literals
        if value == "true":
            return "true"
        if value == "false":
            return "false"

        # Handle string literals
        str_match = re.match(r'"([^"]*)"', value)
        if str_match:
            return str_match.group(1)

        # Handle numeric literals
        try:
            if "." in value:
                return str(float(value))
            return str(int(value))
        except ValueError:
            pass

        return value

    def _extract_constraints(self, attributes: str) -> FieldConstraint | None:
        """Extract constraints from field attributes."""
        is_id = "@id" in attributes
        is_unique = "@unique" in attributes

        # Extract foreign key from @relation
        foreign_key: str | None = None
        # Look for the field being used in a relation on the same model
        # Prisma puts @relation on the relation field, not the FK field
        # But we can detect FK fields by context

        if is_id or is_unique or foreign_key:
            return FieldConstraint(
                primary_key=is_id,
                unique=is_unique,
                foreign_key=foreign_key,
            )
        return None
