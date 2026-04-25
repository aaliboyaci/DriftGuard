"""SQLite schema collector.

Uses SQLAlchemy's inspect to extract table schemas from a SQLite database.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldConstraint, FieldDef, ResourceSchema, SourceType

SQLITE_TYPE_MAP: dict[str, str] = {
    "INTEGER": "integer",
    "INT": "integer",
    "SMALLINT": "integer",
    "BIGINT": "integer",
    "TINYINT": "integer",
    "REAL": "number",
    "FLOAT": "number",
    "DOUBLE": "number",
    "NUMERIC": "number",
    "DECIMAL": "number",
    "TEXT": "string",
    "VARCHAR": "string",
    "CHAR": "string",
    "CLOB": "string",
    "BLOB": "string",
    "BOOLEAN": "boolean",
    "DATE": "string",
    "DATETIME": "string",
    "TIMESTAMP": "string",
}


class SqliteCollector(BaseCollector):
    """Collects schema from a SQLite database via SQLAlchemy inspect."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._connection_string = f"sqlite:///{db_path}"

    @property
    def name(self) -> str:
        return f"sqlite:{self._db_path}"

    def collect(self) -> list[ResourceSchema]:
        engine = create_engine(self._connection_string)
        insp = inspect(engine)
        resources: list[ResourceSchema] = []

        for table_name in insp.get_table_names():
            columns = insp.get_columns(table_name)
            pk_cols = insp.get_pk_constraint(table_name)
            pk_names: set[str] = set(pk_cols.get("constrained_columns", []))

            unique_cols: set[str] = set()
            for uc in insp.get_unique_constraints(table_name):
                unique_cols.update(uc.get("column_names", []))

            fk_map: dict[str, str] = {}
            for fk in insp.get_foreign_keys(table_name):
                ref = f"{fk['referred_table']}.{fk['referred_columns'][0]}" if fk.get("referred_columns") else None
                for col in fk.get("constrained_columns", []):
                    if ref:
                        fk_map[col] = ref

            fields: list[FieldDef] = []
            for col in columns:
                col_name = col["name"]
                type_str = str(col.get("type", "TEXT")).upper().split("(")[0].strip()
                normalized = SQLITE_TYPE_MAP.get(type_str, "string")
                nullable = col.get("nullable", True)

                constraint = FieldConstraint(
                    primary_key=col_name in pk_names,
                    unique=col_name in unique_cols,
                    foreign_key=fk_map.get(col_name),
                )

                fields.append(
                    FieldDef(
                        name=col_name,
                        field_type=normalized,
                        nullable=nullable,
                        required=not nullable,
                        default=str(col["default"]) if col.get("default") is not None else None,
                        constraints=constraint,
                    )
                )

            resources.append(
                ResourceSchema(
                    name=table_name,
                    source_type=SourceType.SQLITE,
                    fields=fields,
                )
            )

        engine.dispose()
        return resources
