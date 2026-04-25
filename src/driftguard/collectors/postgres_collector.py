"""PostgreSQL schema collector.

Uses SQLAlchemy's inspect to extract table schemas from a PostgreSQL database.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldConstraint, FieldDef, ResourceSchema, SourceType

# SQLAlchemy type name to normalized type mapping
PG_TYPE_MAP: dict[str, str] = {
    "INTEGER": "integer",
    "BIGINT": "integer",
    "SMALLINT": "integer",
    "SERIAL": "integer",
    "BIGSERIAL": "integer",
    "NUMERIC": "number",
    "DECIMAL": "number",
    "REAL": "number",
    "FLOAT": "number",
    "DOUBLE PRECISION": "number",
    "DOUBLE_PRECISION": "number",
    "VARCHAR": "string",
    "CHAR": "string",
    "TEXT": "string",
    "CHARACTER VARYING": "string",
    "UUID": "string",
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "JSON": "object",
    "JSONB": "object",
    "ARRAY": "array",
    "DATE": "string",
    "TIME": "string",
    "TIMESTAMP": "string",
    "TIMESTAMP WITHOUT TIME ZONE": "string",
    "TIMESTAMP WITH TIME ZONE": "string",
    "TIMESTAMPTZ": "string",
    "INTERVAL": "string",
    "BYTEA": "string",
    "INET": "string",
    "CIDR": "string",
    "MACADDR": "string",
}


class PostgresCollector(BaseCollector):
    """Collect table schemas from a PostgreSQL database."""

    def __init__(self, connection_string: str, schema: str = "public") -> None:
        self._connection_string = connection_string
        self._schema = schema

    @property
    def name(self) -> str:
        return f"postgres:{self._schema}"

    def collect(self) -> list[ResourceSchema]:
        engine = create_engine(self._connection_string)
        insp = inspect(engine)
        resources: list[ResourceSchema] = []

        table_names = insp.get_table_names(schema=self._schema)

        for table_name in sorted(table_names):
            columns = insp.get_columns(table_name, schema=self._schema)
            pk_info = insp.get_pk_constraint(table_name, schema=self._schema)
            pk_columns = set(pk_info.get("constrained_columns", []))
            unique_constraints = insp.get_unique_constraints(table_name, schema=self._schema)
            unique_columns: set[str] = set()
            for uc in unique_constraints:
                for col in uc.get("column_names", []):
                    unique_columns.add(col)

            fk_map: dict[str, str] = {}
            for fk in insp.get_foreign_keys(table_name, schema=self._schema):
                for local_col, ref_col in zip(
                    fk.get("constrained_columns", []),
                    fk.get("referred_columns", []),
                    strict=False,
                ):
                    ref_table = fk.get("referred_table", "")
                    fk_map[local_col] = f"{ref_table}.{ref_col}"

            fields: list[FieldDef] = []
            for col in columns:
                col_name = col["name"]
                col_type = str(col["type"]).upper()
                # Normalize type
                normalized = PG_TYPE_MAP.get(col_type, "string")
                # Check common prefix matches for parameterized types
                if normalized == "string" and col_type not in PG_TYPE_MAP:
                    for prefix, mapped in PG_TYPE_MAP.items():
                        if col_type.startswith(prefix):
                            normalized = mapped
                            break

                constraints = FieldConstraint(
                    primary_key=col_name in pk_columns,
                    unique=col_name in unique_columns,
                    foreign_key=fk_map.get(col_name),
                )

                fields.append(
                    FieldDef(
                        name=col_name,
                        field_type=normalized,
                        nullable=col.get("nullable", True),
                        required=not col.get("nullable", True),
                        default=str(col["default"]) if col.get("default") is not None else None,
                        constraints=constraints,
                    )
                )

            resources.append(
                ResourceSchema(
                    name=table_name,
                    source_type=SourceType.POSTGRES,
                    fields=fields,
                )
            )

        engine.dispose()
        return resources
