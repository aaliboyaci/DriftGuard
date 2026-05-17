"""Sequelize model file collector.

Parses Sequelize model definitions (JavaScript/TypeScript) using regex patterns.
Extracts model name, table name, fields, types, constraints, and defaults.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from driftguard.collectors.orm.base import BaseOrmCollector
from driftguard.schema.models import FieldConstraint, FieldDef, ResourceSchema, SourceType

# Sequelize DataTypes to normalized type mapping
DATATYPE_MAP: dict[str, str] = {
    "STRING": "string",
    "TEXT": "string",
    "CHAR": "string",
    "INTEGER": "integer",
    "BIGINT": "integer",
    "SMALLINT": "integer",
    "TINYINT": "integer",
    "MEDIUMINT": "integer",
    "FLOAT": "number",
    "DOUBLE": "number",
    "DECIMAL": "number",
    "REAL": "number",
    "BOOLEAN": "boolean",
    "JSON": "object",
    "JSONB": "object",
    "DATE": "string(date)",
    "DATEONLY": "string(date)",
    "TIME": "string(time)",
    "UUID": "string(uuid)",
    "UUIDV1": "string(uuid)",
    "UUIDV4": "string(uuid)",
    "ENUM": "string",
    "ARRAY": "array",
    "BLOB": "string",
    "VIRTUAL": "string",
    "GEOMETRY": "object",
    "GEOGRAPHY": "object",
    "INET": "string",
    "MACADDR": "string",
    "CIDR": "string",
    "RANGE": "array",
    "HSTORE": "object",
}

# Pattern to match sequelize.define('ModelName', { ... }, { options })
_DEFINE_PATTERN = re.compile(
    r"""sequelize\.define\(\s*['"](\w+)['"]\s*,\s*\{""",
    re.MULTILINE,
)

# Pattern to match class ModelName extends Model
_CLASS_PATTERN = re.compile(
    r"""class\s+(\w+)\s+extends\s+Model""",
    re.MULTILINE,
)

# Pattern to match tableName in options
_TABLE_NAME_PATTERN = re.compile(
    r"""tableName\s*:\s*['"](\w+)['"]""",
    re.MULTILINE,
)

# Pattern to match DataTypes.TYPE or DataTypes.TYPE(args)
_DATATYPE_PATTERN = re.compile(
    r"""DataTypes\.(\w+)(?:\(([^)]*)\))?""",
)


class SequelizeCollector(BaseOrmCollector):
    """Collect schemas from Sequelize model files (JS/TS)."""

    def __init__(self, paths: str | Path | list[str | Path]) -> None:
        if isinstance(paths, (str, Path)):
            self._paths = [Path(paths)]
        else:
            self._paths = [Path(p) for p in paths]

    @property
    def name(self) -> str:
        return "sequelize"

    def collect(self) -> list[ResourceSchema]:
        resources: list[ResourceSchema] = []
        for path in self._paths:
            content = path.read_text(encoding="utf-8")
            resource = self._parse_model(content, path)
            if resource:
                resources.append(resource)
        return resources

    def _parse_model(self, content: str, path: Path) -> ResourceSchema | None:
        """Parse a single Sequelize model file."""
        model_name = self._extract_model_name(content)
        if not model_name:
            return None

        table_name = self._extract_table_name(content) or model_name.lower() + "s"
        fields = self._extract_fields(content)

        return ResourceSchema(
            name=table_name,
            source_type=SourceType.SEQUELIZE,
            fields=fields,
            metadata={"model_name": model_name, "file": str(path)},
        )

    def _extract_model_name(self, content: str) -> str | None:
        """Extract model name from define() call or class declaration."""
        match = _DEFINE_PATTERN.search(content)
        if match:
            return match.group(1)
        match = _CLASS_PATTERN.search(content)
        if match:
            return match.group(1)
        return None

    def _extract_table_name(self, content: str) -> str | None:
        """Extract explicit table name from model options."""
        match = _TABLE_NAME_PATTERN.search(content)
        if match:
            return match.group(1)
        return None

    def _extract_fields(self, content: str) -> list[FieldDef]:
        """Extract field definitions from the model body."""
        fields: list[FieldDef] = []

        # Find the fields object block after define( or init(
        # We look for field definitions in format: fieldName: { type: DataTypes.X, ... }
        # or shorthand: fieldName: DataTypes.X
        field_blocks = self._find_field_blocks(content)

        for field_name, field_body in field_blocks:
            field_def = self._parse_field(field_name, field_body)
            if field_def:
                fields.append(field_def)

        return fields

    def _find_field_blocks(self, content: str) -> list[tuple[str, str]]:
        """Find all field name + body pairs in the model definition."""
        results: list[tuple[str, str]] = []

        # Match field definitions like: fieldName: { ... }
        # Uses a brace-counting approach to handle nested braces
        pattern = re.compile(
            r"""(\w+)\s*:\s*\{""",
            re.MULTILINE,
        )

        # First find the model fields section
        # It starts after sequelize.define('Name', { or Model.init({
        define_match = re.search(
            r"""(?:sequelize\.define\(\s*['"]\w+['"]\s*,|\.init\()\s*\{""",
            content,
        )
        if not define_match:
            return results

        start_pos = define_match.end()
        # Find the matching closing brace for the fields object
        fields_end = self._find_matching_brace(content, start_pos - 1)
        if fields_end == -1:
            fields_end = len(content)

        fields_section = content[start_pos:fields_end]

        # Now find individual field blocks
        for match in pattern.finditer(fields_section):
            field_name = match.group(1)
            # Skip known non-field keys
            if field_name in (
                "tableName",
                "timestamps",
                "freezeTableName",
                "underscored",
                "indexes",
                "hooks",
                "validate",
                "scopes",
                "sequelize",
                "modelName",
                "paranoid",
            ):
                continue

            brace_end = self._find_matching_brace(content, start_pos + match.start() + len(match.group(0)) - 1)
            if brace_end != -1:
                field_body = content[start_pos + match.start() + len(match.group(0)) : brace_end]
                results.append((field_name, field_body))

        return results

    def _find_matching_brace(self, content: str, open_pos: int) -> int:
        """Find the position of the matching closing brace."""
        if open_pos >= len(content) or content[open_pos] != "{":
            return -1

        depth = 1
        pos = open_pos + 1
        while pos < len(content) and depth > 0:
            ch = content[pos]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch in ("'", '"', "`"):
                # Skip string literals
                pos += 1
                while pos < len(content) and content[pos] != ch:
                    if content[pos] == "\\":
                        pos += 1
                    pos += 1
            pos += 1

        return pos - 1 if depth == 0 else -1

    def _parse_field(self, field_name: str, field_body: str) -> FieldDef | None:
        """Parse a field body into a FieldDef."""
        # Extract type
        field_type = self._extract_type(field_body)
        if not field_type:
            return None

        # Extract nullable (allowNull)
        nullable = self._extract_nullable(field_body)

        # Extract default value
        default = self._extract_default(field_body)

        # Extract constraints
        constraints = self._extract_constraints(field_body)

        # Extract enum values
        enum_values = self._extract_enum_values(field_body)

        return FieldDef(
            name=field_name,
            field_type=field_type,
            nullable=nullable,
            required=not nullable,
            default=default,
            enum_values=enum_values,
            constraints=constraints,
        )

    def _extract_type(self, field_body: str) -> str | None:
        """Extract and normalize the field type."""
        match = _DATATYPE_PATTERN.search(field_body)
        if not match:
            return None
        raw_type = match.group(1)
        return DATATYPE_MAP.get(raw_type, "string")

    def _extract_nullable(self, field_body: str) -> bool:
        """Extract allowNull value. Default is true in Sequelize."""
        match = re.search(r"allowNull\s*:\s*(true|false)", field_body)
        if match:
            return match.group(1) == "true"
        # Sequelize default: allowNull is true
        return True

    def _extract_default(self, field_body: str) -> Any:
        """Extract defaultValue."""
        match = re.search(r"defaultValue\s*:\s*(?:'([^']*)'|\"([^\"]*)\"|(\w+))", field_body)
        if not match:
            return None
        # Return whichever group matched
        return match.group(1) or match.group(2) or match.group(3)

    def _extract_constraints(self, field_body: str) -> FieldConstraint | None:
        """Extract constraint information."""
        primary_key = bool(re.search(r"primaryKey\s*:\s*true", field_body))
        unique = bool(re.search(r"unique\s*:\s*true", field_body))

        # Foreign key from references
        foreign_key: str | None = None
        ref_match = re.search(
            r"references\s*:\s*\{\s*model\s*:\s*['\"]([\w]+)['\"]"
            r"(?:\s*,\s*key\s*:\s*['\"]([\w]+)['\"])?",
            field_body,
        )
        if ref_match:
            ref_model = ref_match.group(1)
            ref_key = ref_match.group(2) or "id"
            foreign_key = f"{ref_model}.{ref_key}"

        if primary_key or unique or foreign_key:
            return FieldConstraint(
                primary_key=primary_key,
                unique=unique,
                foreign_key=foreign_key,
            )
        return None

    def _extract_enum_values(self, field_body: str) -> list[str] | None:
        """Extract enum values from DataTypes.ENUM(...)."""
        match = re.search(r"DataTypes\.ENUM\(([^)]+)\)", field_body)
        if not match:
            return None
        args = match.group(1)
        values = re.findall(r"""['"]([^'"]+)['"]""", args)
        return values if values else None
